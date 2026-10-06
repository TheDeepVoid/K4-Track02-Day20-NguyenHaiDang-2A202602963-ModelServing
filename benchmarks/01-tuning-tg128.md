# 01 - Tune: thread-count sweep

Model `Qwen3.5-0.8B-Q4_K_M.gguf` · host `Linux-x86_64` · llama.cpp `b10488`
CPU: **8 physical · 16 logical** cores · `ngl=0` · metric `tg128`

| threads (-t) | tg128 (tok/s) | vs best |
|:--|--:|--:|
| 1 | 21.0 | 37% |
| 4 | 53.1 | 94% |
| 8 | 56.5 | 100% |
| 16 | 38.7 | 69% |
| 32 | 22.3 | 39% |

**Tốt nhất**: `-t 8` đạt 56.5 tok/s
**Chậm nhất**: `-t 1` đạt 21.0 tok/s (chênh lệch 2.69×)
**So với mặc định physical-core** (`-t 8`, 56.5 tok/s): 1.00×

Dùng lệnh sau:

```bash
LAB_N_THREADS=8 make bench
```

## Giải thích

Đỉnh tại -t 8, khớp đúng với số physical core của i7-11800H (8P cores). Từ -t 1 lên -t 8, throughput tăng gần tuyến tính (21 → 56.5 tok/s), sau đó giảm mạnh tại -t 16 (38.7) và tiếp tục giảm tại -t 32 (22.3). Đây là đường cong bão hòa memory-bandwidth kinh điển: decode bị giới hạn bởi tốc độ CPU stream model weights từ DRAM, không phải bởi khả năng tính toán. Mỗi physical core có L2 cache riêng và phần băng thông memory riêng, nên tăng core đến đúng số physical core cho băng thông cộng dồn. Vượt qua -t 8, các hyper-thread chia sẻ cùng memory interface của physical core — chúng tranh nhau cache line thay vì cộng thêm băng thông, nên throughput giảm. Tại -t 32, mỗi physical core bị 4 OS thread tranh nhau — overhead context-switch và cache thrash kéo throughput xuống gần mức đơn luồng. Kết quả khớp chính xác với hình dạng kỳ vọng: đầu gối tại physical core count, giảm đối xứng hai bên.
