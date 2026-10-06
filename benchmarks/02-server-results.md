# 02 - Serve: Load Test + Đọc Điểm Bão Hòa

Host `Linux-x86_64` · llama.cpp `b10488` ·
`--parallel 4` · `ctx=2048` · `threads=8` ·
`ngl=0`

| Users | Reqs | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Eff. concurrency | Failures |
|:--|--:|--:|--:|--:|--:|--:|--:|
| 10 | 95 | 1.63 | 4700 | 9500 | 12000 | 8.5 | 0.0% |
| 50 | 102 | 1.73 | 26000 | 31000 | 32000 | 37.4 | 0.0% |

*Effective concurrency = RPS × latency trung bình (Định luật Little) — số request thực sự đang in-flight, bất kể locust mô phỏng bao nhiêu user. Bao gồm cả request đang xếp hàng, nên occupancy/slot ratio có thể hợp lệ vượt 1.0; đây là occupancy, không phải utilisation. Để đo slot utilisation thực sự, dùng server gauge (`make metrics`).*

## Hai lần chạy nói lên điều gì

| Tăng từ 10 lên 50 users | |
|:--|--:|
| Offered load | 5× |
| Throughput thực tế | **1.07×** (21% tuyến tính) |
| P95 latency | **3.26×** |
| Effective concurrency ở 50 users | 37.4 vs `--parallel 4` slots (occupancy/slot ratio 9.35) |

**Đã bão hòa.** Throughput chỉ tăng 1.07× cho 5× offered load, và effective concurrency (37.4) đạt hoặc vượt tất cả 4 decode slots. Điểm bão hòa nằm đâu đó dưới 50 users; load thêm vào sau điểm đó trở thành queue time thay vì throughput.

Throughput tăng 1.07× trong khi P95 tăng 3.26×. Khoảng chênh đó chính là lập luận goodput: vượt qua bão hòa, bạn mua thêm throughput bằng cách tiêu latency — nếu SLO là P95 target thì các request thêm vào không còn được phục vụ trong hạn.

## Nhận xét

Bão hòa rõ ràng ở 50 users: throughput chỉ tăng 1.07× (1.63 → 1.73 RPS) dù offered load tăng 5×, và P95 nhảy 3.26× (9500 → 31000 ms). Con số thuyết phục nhất là effective concurrency ở 50 users: 37.4 request đồng thời in-flight với chỉ 4 decode slots — occupancy ratio 9.35×. Tức mỗi slot có trung bình ~9 request xếp hàng đằng sau. Latency tăng thêm ở 50 users gần như hoàn toàn là queue time: P95 tăng từ 9.5 s lên 31 s, delta ~21.5 s, trong khi compute time mỗi request (P50 ở 10 users) đã là 4.7 s. Tỷ lệ latency tăng 4.5× với throughput gần bằng 0 là dấu hiệu queuing điển hình của Định luật Little.

Để nâng goodput tại SLO P95 ≤ 10 s, knob đầu tiên cần tăng là `--parallel`. Hiện tại 4 slots nghĩa là request thứ 5 trở đi phải xếp hàng ngay. Tăng `--parallel` lên 8 nhân đôi điểm vào hàng mà không cần thêm phần cứng — với Qwen3.5 0.8B ở ctx=512, mỗi slot KV cache chỉ ~50 MB, hoàn toàn nằm trong 15 GB RAM. Thread count giữ nguyên ở -t 8 (physical cores) — thêm slots chia sẻ cùng decode bandwidth, không cộng thêm. Sau `--parallel`, knob tiếp theo là giảm max_tokens mỗi request để rút ngắn slot occupancy, giảm queue depth mà không cần thay đổi phần cứng.
