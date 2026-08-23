# P9-SURROGATE-SOURCE-IDENTITY-001

- Source repository: `Yee-Lee/snowboard-agent`
- Source branch: `llm`
- Immutable source commit: `f18f823146727b50cb3ef15e9e14b51983643406`
- Artifact ID: `M4B-P9-RESIDENCY-SURROGATE-001`
- Protocol version: `1.0`

Verify the delivered files before intake:

```text
311466f963bce806b2c89a1c4f5b3275134312e307386c35631eabfb3d21be76  run_p9_residency_surrogate.py
d5de8fe4144a6c759445f7e45e8867a6bad928177cb28f96d908bbcd59ddb8fe  p9_residency_surrogate_protocol.schema.json
d8310132072e822a316521e3bd1cd21e7f0c8396dd49d82c1c6a64a247b7f7f0  p9-residency-surrogate-lock-v1.json
```

The delivery document requests a single corrected Core ACK and directs Audio to integrate these
exact files without changing production semantics. The attached `--self-test` profile is regression
only and is not eligible for M4A-P9 or LLM Gate 2 evidence.
