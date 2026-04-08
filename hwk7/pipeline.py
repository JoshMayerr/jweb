#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import time
from pathlib import PurePosixPath

import apache_beam as beam
from apache_beam.io import fileio
from apache_beam.options.pipeline_options import PipelineOptions


LOCAL_INPUT = "/Users/joshmayer/Developer/BU/spring26/cs528/jweb/web/*.html"
LOCAL_OUTPUT = "/Users/joshmayer/Developer/BU/spring26/cs528/jweb/hwk7/output/local"
CLOUD_INPUT = "gs://jweb-content/web/*.html"
CLOUD_OUTPUT = "gs://jweb-content/hwk7/output"

LINK_RE = re.compile(r'HREF="(\d+)\.html"')
TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"[A-Za-z]+")


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=LOCAL_INPUT)
    parser.add_argument("--output", default=LOCAL_OUTPUT)
    parser.add_argument("--cloud", action="store_true")
    return parser.parse_known_args()


def page_id_from_path(path: str) -> int:
    return int(PurePosixPath(path).stem)


class ParseHtmlFile(beam.DoFn):
    def process(self, readable_file: fileio.ReadableFile):
        path = readable_file.metadata.path
        page_id = page_id_from_path(path)
        html = readable_file.read_utf8()
        outgoing_links = [int(target) for target in LINK_RE.findall(html)]
        plain_text = TAG_RE.sub(" ", html)
        words = WORD_RE.findall(plain_text.lower())
        yield {
            "page_id": page_id,
            "outgoing_links": outgoing_links,
            "words": words,
        }


def emit_incoming_edges(record: dict[str, object]):
    for target_id in record["outgoing_links"]:
        yield (target_id, 1)


def emit_bigrams(record: dict[str, object]):
    words = record["words"]
    for first, second in zip(words, words[1:]):
        yield (f"{first} {second}", 1)


def format_top_result(label: str, rows: list[tuple[object, int]]):
    ordered = sorted(rows, key=lambda item: (-item[1], item[0]))
    for key, count in ordered:
        yield f"{label}\t{key}\t{count}"


def build_pipeline(pipeline: beam.Pipeline, input_pattern: str, output_prefix: str) -> None:
    parsed = (
        pipeline
        | "Match HTML Files" >> fileio.MatchFiles(input_pattern)
        | "Read HTML Files" >> fileio.ReadMatches()
        | "Parse HTML Files" >> beam.ParDo(ParseHtmlFile())
    )

    outgoing_top = (
        parsed
        | "Outgoing Counts" >> beam.Map(lambda record: (record["page_id"], len(record["outgoing_links"])))
        | "Top Outgoing" >> beam.combiners.Top.Of(5, key=lambda item: item[1])
        | "Format Outgoing" >> beam.FlatMap(lambda rows: format_top_result("outgoing", rows))
    )

    incoming_top = (
        parsed
        | "Incoming Edges" >> beam.FlatMap(emit_incoming_edges)
        | "Count Incoming" >> beam.CombinePerKey(sum)
        | "Top Incoming" >> beam.combiners.Top.Of(5, key=lambda item: item[1])
        | "Format Incoming" >> beam.FlatMap(lambda rows: format_top_result("incoming", rows))
    )

    bigram_top = (
        parsed
        | "Emit Bigrams" >> beam.FlatMap(emit_bigrams)
        | "Count Bigrams" >> beam.CombinePerKey(sum)
        | "Top Bigrams" >> beam.combiners.Top.Of(5, key=lambda item: item[1])
        | "Format Bigrams" >> beam.FlatMap(lambda rows: format_top_result("bigram", rows))
    )

    _ = outgoing_top | "Write Outgoing" >> beam.io.WriteToText(
        f"{output_prefix}/outgoing", file_name_suffix=".txt", shard_name_template=""
    )
    _ = incoming_top | "Write Incoming" >> beam.io.WriteToText(
        f"{output_prefix}/incoming", file_name_suffix=".txt", shard_name_template=""
    )
    _ = bigram_top | "Write Bigrams" >> beam.io.WriteToText(
        f"{output_prefix}/bigrams", file_name_suffix=".txt", shard_name_template=""
    )


def main() -> None:
    args, beam_args = parse_args()

    if args.cloud:
        if args.input == LOCAL_INPUT:
            args.input = CLOUD_INPUT
        if args.output == LOCAL_OUTPUT:
            args.output = CLOUD_OUTPUT

    if not args.output.startswith("gs://"):
        os.makedirs(args.output, exist_ok=True)

    start = time.time()
    options = PipelineOptions(beam_args)
    with beam.Pipeline(options=options) as pipeline:
        build_pipeline(pipeline, args.input, args.output)
    elapsed = time.time() - start
    print(f"Finished in {elapsed:.2f} seconds")
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
