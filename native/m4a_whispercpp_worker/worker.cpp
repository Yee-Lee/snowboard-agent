#include "whisper.h"

#include <chrono>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>
#include <vector>

namespace {

constexpr int kSampleRate = 16000;
constexpr int kMaxThreads = 4;
constexpr std::size_t kMaxSamples = 60U * kSampleRate;
constexpr std::size_t kMaxPromptBytes = 512U;

uint16_t read_u16(std::istream & input) {
    unsigned char bytes[2] = {};
    input.read(reinterpret_cast<char *>(bytes), sizeof(bytes));
    if (!input) {
        throw std::runtime_error("TRUNCATED_WAV");
    }
    return static_cast<uint16_t>(bytes[0]) |
           static_cast<uint16_t>(bytes[1]) << 8U;
}

uint32_t read_u32(std::istream & input) {
    unsigned char bytes[4] = {};
    input.read(reinterpret_cast<char *>(bytes), sizeof(bytes));
    if (!input) {
        throw std::runtime_error("TRUNCATED_WAV");
    }
    return static_cast<uint32_t>(bytes[0]) |
           static_cast<uint32_t>(bytes[1]) << 8U |
           static_cast<uint32_t>(bytes[2]) << 16U |
           static_cast<uint32_t>(bytes[3]) << 24U;
}

std::vector<float> read_pcm16_mono_wav(const std::string & path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("WAV_OPEN_FAILED");
    }
    char id[4] = {};
    input.read(id, 4);
    (void) read_u32(input);
    if (std::memcmp(id, "RIFF", 4) != 0) {
        throw std::runtime_error("WAV_NOT_RIFF");
    }
    input.read(id, 4);
    if (!input || std::memcmp(id, "WAVE", 4) != 0) {
        throw std::runtime_error("WAV_NOT_WAVE");
    }

    bool format_seen = false;
    uint16_t audio_format = 0;
    uint16_t channels = 0;
    uint32_t sample_rate = 0;
    uint16_t bits_per_sample = 0;
    std::vector<char> pcm_bytes;
    while (input && !pcm_bytes.size()) {
        input.read(id, 4);
        if (!input) {
            break;
        }
        const uint32_t chunk_size = read_u32(input);
        if (std::memcmp(id, "fmt ", 4) == 0) {
            if (chunk_size < 16U) {
                throw std::runtime_error("WAV_FMT_TOO_SHORT");
            }
            audio_format = read_u16(input);
            channels = read_u16(input);
            sample_rate = read_u32(input);
            (void) read_u32(input);
            (void) read_u16(input);
            bits_per_sample = read_u16(input);
            input.seekg(static_cast<std::streamoff>(chunk_size - 16U), std::ios::cur);
            format_seen = true;
        } else if (std::memcmp(id, "data", 4) == 0) {
            if (!format_seen || chunk_size == 0U || chunk_size > kMaxSamples * 2U || chunk_size % 2U != 0U) {
                throw std::runtime_error("WAV_DATA_INVALID");
            }
            pcm_bytes.resize(chunk_size);
            input.read(pcm_bytes.data(), static_cast<std::streamsize>(pcm_bytes.size()));
            if (!input) {
                throw std::runtime_error("TRUNCATED_WAV_DATA");
            }
        } else {
            input.seekg(static_cast<std::streamoff>(chunk_size), std::ios::cur);
        }
        if (chunk_size % 2U != 0U) {
            input.seekg(1, std::ios::cur);
        }
    }
    if (audio_format != 1U || channels != 1U || sample_rate != kSampleRate || bits_per_sample != 16U) {
        throw std::runtime_error("WAV_FORMAT_NOT_FROZEN_PCM16_MONO_16KHZ");
    }
    if (pcm_bytes.empty()) {
        throw std::runtime_error("WAV_DATA_MISSING");
    }
    std::vector<float> samples(pcm_bytes.size() / 2U);
    for (std::size_t i = 0; i < samples.size(); ++i) {
        const auto low = static_cast<uint8_t>(pcm_bytes[2U * i]);
        const auto high = static_cast<uint8_t>(pcm_bytes[2U * i + 1U]);
        const auto value = static_cast<int16_t>(static_cast<uint16_t>(low) |
                                                static_cast<uint16_t>(high) << 8U);
        samples[i] = static_cast<float>(value) / 32768.0F;
    }
    return samples;
}

uint64_t monotonic_us() {
    const auto now = std::chrono::steady_clock::now().time_since_epoch();
    return static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::microseconds>(now).count());
}

uint64_t process_cpu_us() {
    struct timespec value = {};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0) {
        throw std::runtime_error("CPU_CLOCK_FAILED");
    }
    return static_cast<uint64_t>(value.tv_sec) * 1000000ULL +
           static_cast<uint64_t>(value.tv_nsec) / 1000ULL;
}

long peak_rss_kib() {
    struct rusage usage = {};
    if (getrusage(RUSAGE_SELF, &usage) != 0) {
        throw std::runtime_error("RSS_READ_FAILED");
    }
    return usage.ru_maxrss;
}

std::string hex_encode(const std::string & value) {
    std::ostringstream output;
    output << std::hex << std::setfill('0');
    for (const unsigned char byte : value) {
        output << std::setw(2) << static_cast<unsigned int>(byte);
    }
    return output.str();
}

enum class Decoder {
    Greedy,
    Beam,
};

std::string transcribe(whisper_context * context, const std::vector<float> & samples,
                       int threads, Decoder decoder, int beam_size,
                       const std::string & initial_prompt) {
    const auto strategy = decoder == Decoder::Greedy
        ? WHISPER_SAMPLING_GREEDY : WHISPER_SAMPLING_BEAM_SEARCH;
    whisper_full_params params = whisper_full_default_params(strategy);
    params.n_threads = threads;
    params.translate = false;
    params.no_context = true;
    params.no_timestamps = true;
    params.single_segment = false;
    params.print_special = false;
    params.print_progress = false;
    params.print_realtime = false;
    params.print_timestamps = false;
    params.token_timestamps = false;
    params.language = "zh";
    params.detect_language = false;
    params.temperature = 0.0F;
    params.temperature_inc = 0.0F;
    params.greedy.best_of = 1;
    params.beam_search.beam_size = beam_size;
    params.beam_search.patience = 1.0F;
    params.initial_prompt = initial_prompt.empty() ? nullptr : initial_prompt.c_str();
    params.carry_initial_prompt = false;
    params.prompt_tokens = nullptr;
    params.prompt_n_tokens = 0;
    params.vad = false;
    params.vad_model_path = nullptr;

    if (whisper_full(context, params, samples.data(), static_cast<int>(samples.size())) != 0) {
        throw std::runtime_error("WHISPER_FULL_FAILED");
    }
    std::string result;
    const int segments = whisper_full_n_segments(context);
    for (int segment = 0; segment < segments; ++segment) {
        const char * text = whisper_full_get_segment_text(context, segment);
        if (text != nullptr) {
            result += text;
        }
    }
    return result;
}

}  // namespace

int main(int argc, char ** argv) {
    std::string model_path;
    int threads = 0;
    Decoder decoder = Decoder::Greedy;
    int beam_size = 5;
    bool beam_size_seen = false;
    std::string initial_prompt;
    bool initial_prompt_seen = false;
    for (int index = 1; index < argc; index += 2) {
        if (index + 1 >= argc) {
            std::cerr << "missing option value" << std::endl;
            return 2;
        }
        const std::string option = argv[index];
        const std::string value = argv[index + 1];
        try {
            if (option == "--model") {
                model_path = value;
            } else if (option == "--threads") {
                threads = std::stoi(value);
            } else if (option == "--decoder") {
                if (value == "greedy") {
                    decoder = Decoder::Greedy;
                } else if (value == "beam") {
                    decoder = Decoder::Beam;
                } else {
                    throw std::invalid_argument("decoder");
                }
            } else if (option == "--beam-size") {
                beam_size = std::stoi(value);
                beam_size_seen = true;
            } else if (option == "--initial-prompt") {
                initial_prompt = value;
                initial_prompt_seen = true;
            } else {
                throw std::invalid_argument("option");
            }
        } catch (const std::exception &) {
            std::cerr << "invalid worker option" << std::endl;
        }
    }
    if (model_path.empty() || threads < 1 || threads > kMaxThreads) {
        std::cerr << "thread count must be between 1 and 4" << std::endl;
        return 2;
    }
    if (beam_size < 1 || beam_size > 16 || (decoder == Decoder::Greedy && beam_size_seen)) {
        std::cerr << "beam size is valid only for beam decoder and must be between 1 and 16" << std::endl;
        return 2;
    }
    bool prompt_has_control = false;
    for (const unsigned char byte : initial_prompt) {
        if (byte < 0x20U || byte == 0x7fU) {
            prompt_has_control = true;
        }
    }
    if ((initial_prompt_seen && initial_prompt.empty()) ||
            initial_prompt.size() > kMaxPromptBytes || prompt_has_control) {
        std::cerr << "initial prompt must be 1 to 512 UTF-8 bytes without control characters"
                  << std::endl;
        return 2;
    }
    if (std::string(whisper_version()) != "1.9.2") {
        std::cerr << "unexpected whisper.cpp version" << std::endl;
        return 3;
    }
    whisper_context_params context_params = whisper_context_default_params();
    context_params.use_gpu = false;
    context_params.flash_attn = false;
    const uint64_t load_started = monotonic_us();
    whisper_context * context = whisper_init_from_file_with_params(model_path.c_str(), context_params);
    if (context == nullptr) {
        std::cerr << "model load failed" << std::endl;
        return 4;
    }
    const uint64_t load_us = monotonic_us() - load_started;
    std::cout << "READY\t1.9.2\t" << load_us << "\t" << getpid() << std::endl;

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line == "QUIT") {
            whisper_free(context);
            std::cout << "BYE" << std::endl;
            return 0;
        }
        constexpr char prefix[] = "TRANSCRIBE\t";
        if (line.rfind(prefix, 0) != 0 || line.size() <= sizeof(prefix) - 1U || line.size() > 4096U) {
            std::cout << "ERROR\tINVALID_COMMAND" << std::endl;
            continue;
        }
        try {
            const auto samples = read_pcm16_mono_wav(line.substr(sizeof(prefix) - 1U));
            const uint64_t wall_started = monotonic_us();
            const uint64_t cpu_started = process_cpu_us();
            const std::string transcript = transcribe(
                context, samples, threads, decoder, beam_size, initial_prompt);
            const uint64_t cpu_us = process_cpu_us() - cpu_started;
            const uint64_t wall_us = monotonic_us() - wall_started;
            std::cout << "RESULT\t" << hex_encode(transcript) << "\t" << wall_us << "\t"
                      << cpu_us << "\t" << peak_rss_kib() << std::endl;
        } catch (const std::exception & error) {
            std::cout << "ERROR\t" << error.what() << std::endl;
        }
    }
    whisper_free(context);
    return 0;
}
