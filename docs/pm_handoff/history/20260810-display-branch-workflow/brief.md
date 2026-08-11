# Display POC branch 開發流程

- 對象：Display POC 團隊
- Owner：內部 Designer
- Status：`Ready for PM delivery`

## 建議流程

- OLED SSD1351 維持 primary：後續以 `dev_display_m{x}` 推進，先完成 Display P1 ~ P4；每次 delivery 仍以 manifest 內完整 40-character SHA 為準。
- OLED P4 取得 `Accepted as M3 design input` 後，Core Team即可推進Core M3 / Core M4，不等待LCD。
- LCD ST7789 維持backup option：需要時從OLED Accepted exact SHA建立 `dev_display_lcd_m1`，後續沿用 `dev_display_lcd_m{x}`，不得改寫已Accepted的OLED branch / SHA / evidence。
- LCD使用獨立config、pin map、manifest與Pi evidence；若修改共用HAL / adapter，須另附OLED regression結果。

Branch名稱只表示工作線，不取代exact SHA，也不代表POC Accepted或Core產品基線。
