#!/usr/bin/env python
import defopt
import sys
import gc
import logging
from pathlib import Path
from typing import Optional
import pandas as pd
import polars as pl
import numpy as np
from numba import njit
import io


def make_decorator(ct, fiber, score, strand, color, el_type, hp, st, en, starts, ends):
    start = starts[0]
    end = ends[-1]
    lengths = ",".join(map(str, ends - starts))
    offsets = ",".join(map(str, starts - start))
    block_count = len(starts)
    # chr1 12 9985 block 1000 + 12 9985 200,0,150
    # 382, 1 , 1
    # chr1:1-10000:LongRead
    # block 255,0,0,180 Ignored TypeA
    return (
        # bed9
        f"{ct}\t{start}\t{end}\t{el_type}\t{score}\t{strand}\t{start}\t{end}\t{color},0\t"
        # bed12
        f"{block_count}\t{lengths}\t{offsets}\t"
        # read tag for the decorator
        f"{ct}:{st}-{en}:{fiber}\t"
        # decorator
        f"block\t{color},0\tIgnored\t{el_type}"
    )


def subgroup(df, ct, fiber, strand, hp):
    st = df["st"].min()
    en = df["en"].max()
    #  st      en      fiber   score   strand  tst     ten     color   qValue  HP
    for (score, strand, color), gdf in df.groupby(["score", "strand", "color"]):
        if color == "230,230,230":
            el_type = "Nucleosome"
            continue
        elif color == "147,112,219":
            el_type = "Linker"
        else:
            el_type = "FIRE"

        decorator = make_decorator(
            ct,
            fiber,
            score,
            strand,
            color,
            el_type,
            hp,
            st,
            en,
            gdf["st"].to_numpy(),
            gdf["en"].to_numpy(),
        )
        print(decorator)

    score = 1
    return (
        ct,
        st,
        en,
        fiber,
        score,
        strand,
        0,
        0,
        "0,0,0,200",
        2,
        "1,1",
        f"0,{en-st-1}",
        hp,
    )


def process(df, outfile):
    data = []
    for (ct, fiber, strand, hp), gdf in df.groupby(["#ct", "fiber", "strand", "HP"]):
        bed12 = subgroup(gdf, ct, fiber, strand, hp)
        data.append(bed12)
    bed12 = pd.DataFrame(data).sort_values([0, 1, 2])
    bed12.to_csv(outfile, sep="\t", header=False, index=False)


def main(
    infile: str,
    outfile: Optional[Path],
    *,
    verbose: int = 0,
):
    """
    Author Mitchell R. Vollger

    :param infile: Input file, stdin by default
    :param outfile: Output file, stdout by default
    :param verbose: Set the logging level of the function
    """
    if infile == "-":
        infile = io.StringIO(sys.stdin.read())
    outfile = open(outfile, "w")

    logger = logging.getLogger()
    log_format = "[%(levelname)s][Time elapsed (ms) %(relativeCreated)d]: %(message)s"
    log_level = 10 * (3 - verbose)
    logging.basicConfig(format=log_format)
    logger.setLevel(log_level)

    df = pl.read_csv(
        infile,
        separator="\t",
        # comment_char="#",
    )
    logging.info(f"{df}")
    process(df, outfile)
    return 0


if __name__ == "__main__":
    defopt.run(main, show_types=True, version="0.0.1")
