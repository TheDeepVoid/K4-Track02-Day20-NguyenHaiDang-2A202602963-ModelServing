# Bonus - Sweep Độ Dài Context (chi phí prefill)

Host `Linux-x86_64` · llama.cpp `b10488` ·
`threads=8` `ngl=0` · RAM 15.3 GB

| Số token prompt | Prefill (tok/s) | TTFT đóng góp (ms) | So với tuyến tính |
|:--|--:|--:|--:|
| 256 | 169.6 | 1509.1 | 1.00× |
| 1024 | 154.6 | 6624.0 | 1.10× |
| 2048 | 298.0 | 6872.9 | 0.57× |
| 4096 | 275.3 | 14877.2 | 0.62× |
| 8192 | 271.8 | 30143.1 | 0.62× |

Ở 8192 token, prefill tốn **30143 ms** — tức **0.62×** tuyến tính, nghĩa là trong dải này prefill **vẫn tăng gần tuyến tính**, chưa bẻ cong bậc hai.

Đây là kết quả đúng, không phải thí nghiệm thất bại. Attention là O(N²) nhưng chỉ là một hạng tử: các phép chiếu tuyến tính và MLP là O(N), và trên model nhỏ (0.8B) chúng vẫn chiếm tỷ trọng lớn hơn ở dải context ngắn này.

Để tìm điểm bẻ cong thật sự, mở rộng grid:

```bash
.venv/bin/python bonus/sweeps/ctx-len-sweep.py --grid 1024,4096,8192,16384,32768
```

## Nhận xét

**Tại sao đường cong chưa bẻ cong bậc hai trong dải 256–8192 token?**

Attention có độ phức tạp O(N²) theo số token, nhưng đây chỉ là một trong nhiều hạng tử chi phí của mỗi transformer layer. Cụ thể, mỗi layer gồm:
- **Attention:** O(N² · d_head) — bậc hai theo N
- **Linear projections (Q/K/V/O):** O(N · d_model²) — tuyến tính theo N
- **MLP (FFN):** O(N · d_model · d_ffn) — tuyến tính theo N

Với Qwen3.5 0.8B (d_model=1024, d_ffn=3072, 28 layers), chi phí MLP và projection lớn hơn attention ở N nhỏ. Điểm mà attention bắt đầu dominate phụ thuộc vào kích thước model: với 0.8B thường rơi vào 16K–32K token trở lên. Trên GPU lớn với model 70B+, điểm này thấp hơn nhiều (~2K–4K token).

**Hệ quả thực tế cho RAG trên máy này:**

Mỗi chunk 256 token tốn 1509 ms TTFT. Nhồi 4 chunk (1024 token) tốn 6624 ms — tăng ~4.4× so với 1 chunk. Đây vẫn là tuyến tính, nhưng 6.6 giây chờ trước token đầu tiên là không chấp nhận được với user-facing application. Pipeline RAG trên máy này nên:
- Giới hạn context ở khoảng **512–1024 token** (2–4 chunk ngắn) để giữ TTFT dưới 3 giây
- Dùng retrieval chính xác (BM25 + reranker) thay vì nhồi nhiều chunk kém relevance
- Nhớ rằng **prefill là chi phí trả trước, trên mỗi request** — không được amortize qua các token decode như decode cost

Với người đề xuất "nhồi thêm context vì context window cho phép": TTFT trả giá tuyến tính ngay cả khi bậc hai chưa lộ — 30 giây chờ ở 8192 token là bằng chứng đủ thuyết phục.
