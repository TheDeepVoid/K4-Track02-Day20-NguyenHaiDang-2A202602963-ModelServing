# Bonus - Sweep Batch Size (chunked prefill)

Host `Linux-x86_64` · llama.cpp `b10488` ·
`threads=8` `ngl=0` · metric `pp512`

| -b (logical) | -ub (micro) | pp512 (tok/s) | vs tốt nhất |
|:--|--:|--:|--:|
| 128 | 128 | 330.1 | 96% |
| 256 | 256 | 339.7 | 99% |
| 512 | 256 | 344.3 | 100% |
| 512 | 512 | 322.1 | 94% |
| 1024 | 512 | 318.1 | 92% |
| 2048 | 512 | 304.5 | 88% |

Tốt nhất: `-b 512 -ub 256` đạt 344.3 tok/s (1.13× so với điểm chậm nhất).

Sweep này chỉ đo nửa throughput của bài toán. Chi phí ẩn là TTFT cho các request đang chờ: micro-batch lớn hơn giữ device lâu hơn mỗi bước, nên mọi thứ đứng sau phải chờ lâu hơn. Để thấy cả hai mặt, chạy lại `make load-50` với setting tốt nhất và tệ nhất qua `.venv/bin/python labs/02-serve/serve.py -- -b N -ub M` rồi so sánh P95.

## Nhận xét

**`-b 512 -ub 256` là lựa chọn tốt nhất cho máy này.** Đây là lý do:

**Cơ chế của `-b` và `-ub`:**
- `-b` (logical batch): số token tối đa được xử lý trong một bước prefill. Lớn hơn → ít bước hơn → overhead per-step được amortize tốt hơn → throughput tăng.
- `-ub` (micro-batch / physical batch): kích thước thực tế của mỗi chunk được đưa vào kernel. Đây là knob kiểm soát độ dài mỗi lần "hold device".

Hai tham số này tương tự chunked prefill trong vLLM: `-b` là kích thước prefill chunk tối đa, `-ub` là kích thước mỗi lần tính toán thực sự.

**Tại sao `-ub 256` tốt hơn `-ub 512` khi `-b=512`?**
Các prompt trong lab (~37–150 token) nhỏ hơn nhiều so với `-ub 512`. Khi micro-batch lớn hơn actual prompt, kernel phải padding phần còn lại — các slot padding không làm việc thực nhưng vẫn tiêu tốn băng thông bộ nhớ và FLOP. Với `-ub 256`, padding overhead nhỏ hơn và kernel được feed đủ work để vector unit hoạt động hiệu quả mà không waste.

**Tại sao `-b` và `-ub` lớn hơn (1024/2048) lại chậm hơn?**
Khi `-ub` cố định ở 512 nhưng `-b` tăng lên 1024–2048, mỗi bước prefill phải chia nhỏ thành nhiều micro-batch hơn với overhead scheduling tăng. Trên CPU không có hardware prefetcher đủ mạnh để lookahead xa, overhead này tích lũy thành throughput loss (~8–12% so với best point).

**Cần đo thêm gì trước khi deploy production:**
Chạy `make load-50` với `-b 512 -ub 256` và so với baseline không có flag. Nếu P95 giữ nguyên hoặc giảm → deploy an toàn. Nếu P95 tăng → micro-batch đang hold slot quá lâu, hạ `-ub` xuống 128.
