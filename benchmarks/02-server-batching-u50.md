# 02 - Continuous batching under load (u50)

Host `Linux-x86_64` · `--parallel 4` · 30 samples over
60s at 2.0s intervals · raw CSV: `02-server-metrics-u50.csv`

| Gauge | Peak observed |
|:--|--:|
| `n_busy_slots_per_decode` (avg/decode) | 4.00 of 4 slots (100%) |
| `requests_processing` | 4 |
| `requests_deferred` | 46 |
| `kv_cache_usage_ratio` | n/a — not exported by llama.cpp `b10488` |
| `tokens_predicted_total` (final) | 27355 |

Giá trị cao nhất lấy mẫu được là **4.00 / 4** slots. Lưu ý gauge này là *trung bình* busy slots mỗi bước decode của llama.cpp — không phải số tức thời tối đa. Peak gần 1 nghĩa là các request được phục vụ lần lượt — tải quá nhẹ hoặc request đến quá thưa. Peak tiệm cận `--parallel` nghĩa là scheduler đang đóng gói thực sự các request đồng thời vào chung decode step.
`requests_deferred` vượt 0: có nhiều request đến hơn số slot available, nên một số phải chờ. Thời gian chờ đó chính là queue time trong P95 của bạn.

## Nhận xét

Peak `n_busy_slots_per_decode` là **4.00 / 4 slots (100%)** — scheduler đã lấp đầy mọi decode slot trong lần chạy u50. Con số này thống nhất với effective concurrency 37.4 trong `02-server-results.md`, nhưng hai số đo khác nhau thứ khác nhau: server gauge báo slot occupancy thực tế trong decode steps (tối đa 4), còn Little's Law cho tổng occupancy bao gồm cả hàng đợi (37.4). Hai con số không mâu thuẫn — 37.4 request đang in-flight với chỉ 4 slots nghĩa là ~33 request đang xếp hàng trong khi 4 request đang được decode. Server gauge xác nhận continuous batching hoạt động (có — tất cả slots bận); Little's Law cho biết hàng đợi dài bao nhiêu. `requests_deferred` đạt 46 xác nhận thêm: server đã phải deferring các request vượt quá 4 slots nó có thể xử lý ngay.
