# Bonus B4 / C2 - Quantization KV Cache

Host `Linux-x86_64` · llama.cpp `b10488` ·
model `Qwen3.5-0.8B-Q4_K_M.gguf` · `threads=8` `ngl=0` · metric `tg128`, 3 lần lặp

| Kiểu KV (-ctk / -ctv) | tg128 (tok/s) | vs f16 | RAM KV tại ctx=2048, 4 slots |
|:--|--:|--:|--:|
| f16 (mặc định) | 56.29 | 1.00× | ~268 MB |
| q8_0 | 53.99 | 0.96× | ~134 MB |
| q4_0 | 55.00 | 0.98× | ~67 MB |

Ước tính RAM KV: `ctx_size × n_layers × 2 (K+V) × 2 (bytes f16) × n_heads_kv × head_dim ÷ 1e6 × n_slots`.
Qwen3.5 0.8B: 28 layers, 8 KV heads, head_dim=128. f16=2B, q8=1B, q4=0.5B.

## Nhận xét

**Quantization KV cache trên CPU này gần như không tăng tốc decode: f16→q8_0 là 0.96× (−4%), f16→q4_0 là 0.98× (−2%).** Đây là kết quả đúng và có lý giải cụ thể:

**Tại sao KV quant không giúp tốc độ ở đây?**

Decode (tg128) bị giới hạn bởi băng thông tải **model weights**, không phải KV cache. Mỗi token sinh ra yêu cầu đọc toàn bộ ~497 MB model weights từ DRAM — một lần mỗi token, bất kể prompt dài hay ngắn. Ở 128 token output, KV cache chỉ tăng từ 0 đến khoảng `128 × 8 heads × 128 head_dim × 2 bytes = ~0.26 MB` — nhỏ hơn 2000 lần so với weights cần load. Bandwidth dành cho KV là noise so với bandwidth dành cho weights.

Nói cách khác: bottleneck là con đường từ DRAM đến CPU đã bão hòa vì weights. Giảm thêm KV traffic không giải phóng thêm bandwidth có ý nghĩa — pipeline đã đầy ở chỗ khác.

**Vậy KV quant có ích ở đâu?**

KV cache trở thành bottleneck thực sự trong hai tình huống:

1. **Context rất dài (>8K–16K token):** Lúc này KV cache có thể lên tới hàng GB. Ví dụ: 16K token × 28 layers × 2 (K+V) × 8 heads × 128 head_dim × 2 bytes ≈ 14 GB — lớn hơn cả model weights. Trong trường hợp này q8_0 cắt một nửa, q4_0 cắt ba phần tư.

2. **GPU với VRAM giới hạn hoặc nhiều slot song song:** Trên GPU, KV cache thường cạnh tranh VRAM với weights. Quantize KV từ f16 xuống q8_0 giải phóng VRAM để tăng `--parallel` hoặc chạy model lớn hơn mà không OOM.

**Lợi ích thực tế trên máy này — bộ nhớ, không phải tốc độ:**

Chuyển từ f16 sang q4_0 giảm KV RAM từ ~268 MB xuống ~67 MB cho 4 slots ở ctx=2048 — tiết kiệm ~200 MB. Với 15.3 GB RAM, điều này cho phép tăng từ 4 lên 6–7 `--parallel` slots trong cùng RAM budget. Lợi ích gián tiếp: thêm slots giảm queue depth dưới tải cao, từ đó cải thiện P95 — **không phải bằng cách decode nhanh hơn mà bằng cách ít request phải chờ hơn**.

**Kết luận:** trên model nhỏ, context ngắn, CPU-only — bỏ qua KV quant nếu mục tiêu là tốc độ. Dùng nó khi cần nhét thêm parallel slots vào RAM giới hạn.
