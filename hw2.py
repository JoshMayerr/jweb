#!/usr/bin/env python3
# 1. get files from google cloud storage
# 2. loop through files
# 3. for each file, count outdegree and in-degree and add to adjacency list
# 4. write adjacency list to file
# 5. read adjacency list from file
# 6. calculate stats of outdegree and in-degree distributions
# 7. iterate to calculate page rank, stopping at a certain threshold

# example html file:
# <!DOCTYPE html>
# <html>
# <body>
# Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad
# minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
# cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
# <p>
# <a HREF="13781.html"> This is a link </a>
# <p>
# </body>
# </html>

import argparse
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from google.cloud import storage



def list_blobs(bucket_name: str, prefix: str = "web/") -> list:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    return [b.name for b in bucket.list_blobs(prefix=prefix) if b.name.endswith(".html")]


def download_and_parse_blob(bucket, blob_name: str) -> tuple[int, list[int]]:
    blob = bucket.blob(blob_name)
    html = blob.download_as_string().decode("utf-8", errors="replace")
    # example blob_name: web/0.html
    page_id = int(blob_name.rsplit("/", 1)[-1].split(".", 1)[0])
    outgoing = parse_html_links(html)
    return page_id, outgoing


def parse_html_links(html_content: str) -> list[int]:
    soup = BeautifulSoup(html_content, "html.parser")
    ids = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        try:
            ids.append(int(href.split(".", 1)[0]))
        except ValueError:
            pass
    return ids


def build_graph_from_stream(stream, page_ids: set):
    adjacency_list = {}
    for page_id, outgoing in stream:
        adjacency_list[page_id] = list(outgoing)
    all_ids = set(page_ids)
    for pid in list(adjacency_list.keys()):
        if pid not in all_ids:
            del adjacency_list[pid]
        else:
            adjacency_list[pid] = [t for t in adjacency_list[pid] if t in all_ids]
    return all_ids, adjacency_list


def build_reverse_adjacency(adjacency_list: dict, all_ids: set) -> dict[int, list[int]]:
    rev = {nid: [] for nid in all_ids}
    for src, targets in adjacency_list.items():
        for t in targets:
            if t in rev:
                rev[t].append(src)
    return rev


def out_degrees(adjacency_list: dict, all_ids: set) -> dict[int, int]:
    return {nid: len(adjacency_list.get(nid, [])) for nid in all_ids}


def in_degrees(reverse_adjacency: dict) -> dict[int, int]:
    return {nid: len(incoming) for nid, incoming in reverse_adjacency.items()}


def degree_stats(degree_dict: dict) -> tuple[float, float, int, int, list[float]]:
    vals = list(degree_dict.values())
    if not vals:
        return 0.0, 0.0, 0, 0, []
    return (
        sum(vals) / len(vals),
        statistics.median(vals),
        max(vals),
        min(vals),
        statistics.quantiles(vals, n=5),
    )


def print_stats(out_deg: dict, in_deg: dict) -> None:
    o_avg, o_med, o_max, o_min, o_quint = degree_stats(out_deg)
    i_avg, i_med, i_max, i_min, i_quint = degree_stats(in_deg)
    print("Outgoing links:")
    print(f"  avg={o_avg:.4f}  median={o_med}  max={o_max}  min={o_min}  quintiles={o_quint}")
    print("Incoming links:")
    print(f"  avg={i_avg:.4f}  median={i_med}  max={i_max}  min={i_min}  quintiles={i_quint}")


def pagerank(
    adjacency_list: dict,
    reverse_adjacency: dict,
    all_ids: set,
    conv_threshold: float = 0.005,
) -> dict[int, float]:
    n = len(all_ids)
    ids_list = sorted(all_ids)
    pr = {i: 1.0 / n for i in ids_list}

    def out_degree(node):
        c = len(adjacency_list.get(node, []))
        return c if c > 0 else 1

    while True:
        new_pr = {}
        for a in ids_list:
            incoming = reverse_adjacency.get(a, [])
            contrib = sum(pr[t] / out_degree(t) for t in incoming)
            new_pr[a] = 0.15 / n + 0.85 * contrib
        total_old = sum(pr.values())
        total_new = sum(new_pr.values())
        if total_old == 0:
            break
        if abs(total_new - total_old) / total_old <= conv_threshold:
            break
        pr = new_pr
    return pr


def top_k_pagerank(pr: dict[int, float], k: int = 5) -> list[tuple[int, float]]:
    sorted_pr = sorted(pr.items(), key=lambda x: -x[1])
    return sorted_pr[:k]


def run_pipeline(all_ids: set, adjacency_list: dict) -> None:
    print("Running pipeline...")
    rev = build_reverse_adjacency(adjacency_list, all_ids)
    out_deg = out_degrees(adjacency_list, all_ids)
    in_deg = in_degrees(rev)
    print_stats(out_deg, in_deg)
    print("starting PageRank...")
    pr = pagerank(adjacency_list, rev, all_ids)
    print("PageRank calculated.")
    top5 = top_k_pagerank(pr, 5)
    print("Top 5 by PageRank:")
    for pid, score in top5:
        print(f"  {pid}  {score:.6f}")


def run_test() -> None:
    # example graph: 0 -> 1 -> 2 -> 0
    # all_ids: {0, 1, 2}
    # the page rank of each page should be 1/3 and sum to 1
    all_ids = {0, 1, 2}
    adjacency_list = {0: [1], 1: [2], 2: [0]}
    rev = build_reverse_adjacency(adjacency_list, all_ids)
    out_deg = out_degrees(adjacency_list, all_ids)
    in_deg = in_degrees(rev)

    assert out_deg == {0: 1, 1: 1, 2: 1}, out_deg
    assert in_deg == {0: 1, 1: 1, 2: 1}, in_deg

    o_avg, o_med, o_max, o_min, _ = degree_stats(out_deg)
    assert o_avg == 1.0 and o_med == 1 and o_max == 1 and o_min == 1
    i_avg, i_med, i_max, i_min, _ = degree_stats(in_deg)
    assert i_avg == 1.0 and i_med == 1 and i_max == 1 and i_min == 1

    pr = pagerank(adjacency_list, rev, all_ids, conv_threshold=1e-9)
    for pid in all_ids:
        assert abs(pr[pid] - 1.0 / 3) < 1e-5, (pid, pr[pid])
    assert abs(sum(pr.values()) - 1.0) < 1e-6

    print("All tests passed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    parser.add_argument(
        "--workers",
        type=int,
        default=16,
        help="Parallel GCS download workers (default 16, use 1 for sequential)",
    )
    args = parser.parse_args()

    if args.test:
        run_test()
        return

    bucket_name = "jweb-content"
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob_names = list_blobs(bucket_name, "web/")
    if not blob_names:
        print("No HTML blobs found.")
        return

    n_blobs = len(blob_names)
    print(f"Found {n_blobs} blobs, downloading and parsing...")

    blob_ids = {int(n.rsplit("/", 1)[-1].split(".", 1)[0]) for n in blob_names}

    def gcs_stream(workers: int = 1):
        if workers <= 1:
            for name in blob_names:
                yield download_and_parse_blob(bucket, name)
            return
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {
                ex.submit(download_and_parse_blob, bucket, name): name
                for name in blob_names
            }
            for future in as_completed(futures):
                yield future.result()

    def progress_stream(stream, total: int, step: int = 1000):
        for i, item in enumerate(stream, 1):
            if i % step == 0 or i == total:
                print(f"  {i}/{total} blobs")
            yield item

    all_ids, adjacency_list = build_graph_from_stream(
        progress_stream(gcs_stream(workers=args.workers), n_blobs), page_ids=blob_ids
    )
    print("Building graph and running PageRank...")
    run_pipeline(all_ids, adjacency_list)


if __name__ == "__main__":
    main()
