import numpy as np

def analyze_blocks(data_array, block_size, fg_mask=None):
    """
    Computes statistics on a grid for any given input 2D array.
    """
    h, w = data_array.shape
    bh, bw = h // block_size, w // block_size

    # Prepare containers
    stats = {
        "mean": np.zeros((bh, bw), dtype=np.float32),
        "count": np.zeros((bh, bw), dtype=np.int32)
    }

    for by in range(bh):
        for bx in range(bw):
            y0, x0 = by * block_size, bx * block_size
            y1, x1 = min(y0 + block_size, h), min(x0 + block_size, w)
            
            block = data_array[y0:y1, x0:x1]

            if fg_mask is not None:
                mask_block = fg_mask[y0:y1, x0:x1].astype(bool)
                block = block[mask_block]

            if block.size > 0:
                stats["mean"][by, bx] = np.mean(block)
                stats["count"][by, bx] = block.size
            else:
                stats["mean"][by, bx] = np.nan
                stats["count"][by, bx] = 0

    return stats