# Bonus - Quantization Sweep (Qwen3.5 0.8B, Unsloth Dynamic ladder)

Host `Linux-x86_64` · llama.cpp `b10488` ·
`threads=8` `ngl=0` · metric `tg128`

| Quantization | Size (GB) | tg128 (tok/s) | vs UD-Q4_K_XL | tok/s per GB |
|:--|--:|--:|--:|--:|
| UD-Q2_K_XL | 0.39 | 62.0 | 1.16x | 158.8 |
| UD-Q4_K_XL | 0.52 | 53.4 | 1.00x | 102.7 |
| UD-Q6_K_XL | 0.72 | 41.1 | 0.77x | 57.1 |

Decode bị giới hạn bởi memory bandwidth — ít byte/weight hơn thường đồng nghĩa với nhiều token/giây hơn. Cột `tok/s per GB` cho thấy bạn đang thu lại được bao nhiêu tốc độ cho mỗi gigabyte dung lượng bỏ ra.

Tốc độ chỉ là một nửa bài toán. Nửa còn lại là chất lượng — không có benchmark nào ở đây đo được điều đó. Hãy serve hai model (`make serve` và `.venv/bin/python labs/02-serve/serve.py --compare`) rồi hỏi cùng ba câu trước khi kết luận.

## Nhận xét

**Tôi sẽ ship UD-Q2_K_XL trên máy này.** Lý do có hai tầng:

**Tầng 1 — tốc độ:** UD-Q2_K_XL (62.0 tok/s) nhanh hơn UD-Q4_K_XL (53.4 tok/s) 1.16× và nhỏ hơn (0.39 vs 0.52 GB). Trên CPU-only với bottleneck là DRAM bandwidth, ít byte/weight hơn trực tiếp = ít bytes phải stream từ RAM mỗi token = nhanh hơn tương ứng. UD-Q6_K_XL (41.1 tok/s, 0.72 GB) không đáng: to hơn 38% so với UD-Q2_K_XL nhưng chậm hơn 34% — không có lý do để chọn nó trên machine này.

**Tầng 2 — điều bất ngờ về định dạng quant:** UD-Q4_K_XL (53.4 tok/s) chậm hơn Q4_K_M (54.0 tok/s trong benchmark gốc) dù đều là "4-bit". Đây là điểm quan trọng mà deck không nói rõ. Unsloth Dynamic (UD) dùng **mixed precision**: các layer nhạy cảm (embedding, attention output projection, lm_head) được giữ ở precision cao hơn — thường Q6 hoặc Q8 — trong khi phần còn lại mới là Q4 hoặc Q2. Kết quả là effective bytes/weight của UD-Q4_K_XL cao hơn flat Q4_K_M, nên DRAM phải truyền nhiều hơn mỗi token, dẫn đến tốc độ decode thấp hơn một chút.

Điều này có nghĩa: **không thể so sánh quant chỉ bằng số bit nominal** — phải đo tốc độ thực tế trên hardware của mình. UD-Q2_K_XL "thắng kép": nhờ UD dynamic precision, các layer quan trọng vẫn ở Q4/Q6 nên quality không bị degraded nhiều như flat Q2 thông thường, trong khi phần lớn weights (MLP layers) ở Q2 thật sự giúp giảm bytes/weight và tăng tốc decode.

**Điểm dừng:** UD-Q2_K_XL là điểm hợp lý vì Unsloth giữ các layer nhạy cảm ở precision đủ cao để output coherent. Với flat Q2_K (không phải UD), output thường bắt đầu incoherent — đó là lý do UD tồn tại.
