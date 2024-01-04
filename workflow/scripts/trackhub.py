#!/usr/bin/env python
import os
import defopt
import logging
from pathlib import Path
import numpy as np
from typing import Optional


HUB = """
hub {sample}-fiberseq
shortLabel {sample}-fiberseq
longLabel {sample}-fiberseq
genomesFile genomes.txt
email mvollger.edu
"""

GENOMES = """
genome {ref}
trackDb trackDb.txt
"""

BB_TEMPLATE = """
track {sample}-{name}
shortLabel {sample}-{name}
longLabel {sample}-{name}
type bigBed 
bigDataUrl {file}
visibility dense
maxItems 100000
priority 30
"""

TRACK_COMP = """
track {sample}-{hap}-reads
compositeTrack on
shortLabel {sample}-{hap}-reads
longLabel {sample}-{hap}-reads
type bigBed 9 +
maxItems 100000
maxHeightPixels 200:200:1
"""

SUB_COMP_TRACK = """
    track bin-{i}-{sample}-{hap}
    parent reads-{sample}-{hap}
    bigDataUrl bins/{hap}.bin.{i}.bed.bb
    shortLabel {hap}.bin.{i}
    longLabel {hap}.bin.{i}
    priority {i}
    type bigBed 9 +
    itemRgb on
    visibility {viz}
    maxHeightPixels 1:1:1
"""

# type bigBed 6 + 4
FIRE_TEMPLATE = """
track {sample}-FIRE-peaks
type bigNarrowPeak
bigDataUrl {file}
shortLabel {sample}-FIRE-peaks
longLabel {sample}-FIRE-peaks
visibility dense
maxHeightPixels 50:50:1
priority 10
"""

HAP_TEMPLATE = """
track {sample}-hap-differences
type bigBed 9 +
itemRgb on
bigDataUrl {file}
shortLabel {sample}-hap-differences
longLabel {sample}-hap-differences
visibility dense
maxHeightPixels 25:25:1
priority 20
"""


BW_COMP = """
track {sample}-{hap}-FDR
compositeTrack on
shortLabel {hap} FDR tracks 
longLabel {hap} FDR tracks
type bigWig 0 1000
autoScale off
viewLimits {FDR_min}:{FDR_max}
maxItems 100000
maxHeightPixels 50:50:1
"""

BW_TEMPLATE = """
    track FDR.{sample}.{hap}.{nm}
    parent {sample}-{hap}-FDR
    bigDataUrl {file}
    shortLabel FDR.{sample}.{hap}.{nm}
    longLabel FDR.{sample}.{hap}.{nm}
    type bigWig
    visibility {viz}
    priority {i}
    maxHeightPixels 50:50:1
"""

# transparentOverlay
PER_ACC_COMP = """
track {sample}-percent-accessible
shortLabel {sample}-percent-accessible
longLabel  {sample}-percent-accessible
graphTypeDefault points
aggregate transparentOverlay
container multiWig
aggregate none 
showSubtrackColorOnUi on
type bigWig 0 1000
alwaysZero on
viewLimits 0:100
autoScale off
maxItems 100000
visibility full
maxHeightPixels 100:50:8
priority 100
"""

PER_ACC_TEMPLATE = """
    track {sample}-{hap}-percent-accessible
    parent {sample}-percent-accessible
    shortLabel {sample}-{hap}-percent-accessible
    longLabel  {sample}-{hap}-percent-accessible
    bigDataUrl {file}
    type bigWig
    visibility {viz}
    color {color}
"""

FIRE_SCORE_COMP = """
track {sample}-FIRE-score
shortLabel {sample}-FIRE-score
longLabel  {sample}-FIRE-score
graphTypeDefault points
aggregate transparentOverlay
container multiWig
aggregate none 
showSubtrackColorOnUi on
type bigWig 0 1000
alwaysZero on
viewLimits 0:100
autoScale off
maxItems 100000
visibility full
maxHeightPixels 100:50:8
priority 10
"""

FIRE_SCORE = """
    track {sample}-{hap}-FIRE-score
    parent {sample}-FIRE-score
    shortLabel {sample}-{hap}-FIRE-score
    longLabel  {sample}-{hap}-FIRE-score
    bigDataUrl {file}
    type bigWig
    visibility {viz}
    color {color}
"""


MULTI_WIG = """
track {sample}-{hap}-coverage
longLabel {sample}-{hap}-coverage
shortLabel {sample}-{hap}-coverage
container multiWig
aggregate stacked
showSubtrackColorOnUi on
type bigWig 0 1000
autoScale off
alwaysZero on
viewLimits 0:{upper_coverage}
visibility full
maxHeightPixels 100:50:8
priority 90
    
    track {sample}-{hap}-accessible
    parent {sample}-{hap}-coverage
    bigDataUrl {acc}
    type bigWig
    color 139,0,0
    
    track {sample}-{hap}-linker
    parent {sample}-{hap}-coverage
    bigDataUrl {link}
    type bigWig
    color 147,112,219
    
    track {sample}-{hap}-nucleosome
    parent {sample}-{hap}-coverage
    bigDataUrl {nuc}
    type bigWig
    color 169,169,169
    """


FIRE_SCORE_AND_FDR = """
track {sample}-FIRE-FDR
compositeTrack on
shortLabel {sample}-FIRE-FDR
longLabel {sample}-FIRE-FDR
visibility full
type bigWig
maxItems 100000
maxHeightPixels 100:50:1
alwaysZero on
priority 10

    track {sample}-log-fdr
    parent {sample}-FIRE-FDR
    bigDataUrl {fdr}
    shortLabel {sample} -10log10 FDR
    longLabel {sample} -10log10 FDR
    autoScale on
    visibility full
    yLineOnOff on
    yLineMark {y_line}
    gridDefault on
"""

DECORATED = """
track {sample}-{hap}-fibers
shortLabel {sample}-{hap}-fibers
longLabel {sample}-{hap}-fibers
visibility dense
type bigBed 12 +
itemRgb On
filterText.keywords {hap}
bigDataUrl bb/fire-fibers.bb 
decorator.default.bigDataUrl bb/fire-fiber-decorators.bb 
decorator.default.filterValues.keywords 5mC,m6A,NUC,LINKER,FIRE
decorator.default.filterValuesDefault.keywords LINKER,FIRE
priority 80
"""


def generate_trackhub(
    trackhub_dir,
    ref,
    sample,
    max_bins,
    ave_coverage,
):
    if ref == "T2Tv2.0":
        ref = "GCA_009914755.4"

    upper_coverage = int(ave_coverage + 5 * np.sqrt(ave_coverage))
    os.makedirs(f"{trackhub_dir}/", exist_ok=True)
    open(f"{trackhub_dir}/hub.txt", "w").write(HUB.format(sample=sample))
    open(f"{trackhub_dir}/genomes.txt", "w").write(GENOMES.format(ref=ref))
    trackDb = open(f"{trackhub_dir}/trackDb.txt", "w")

    for hap in ["all", "hap1", "hap2", "unk"]:
        # add coverage tracks
        if hap != "unk":
            acc = f"bw/{hap}.fire.coverage.bw"
            nuc = f"bw/{hap}.nucleosome.coverage.bw"
            link = f"bw/{hap}.linker.coverage.bw"
            trackDb.write(
                MULTI_WIG.format(
                    acc=acc,
                    link=link,
                    nuc=nuc,
                    sample=sample,
                    hap=hap,
                    upper_coverage=upper_coverage,
                )
            )

        if hap == "all":
            file = f"bb/FDR-FIRE-peaks.bb"
            trackDb.write(FIRE_TEMPLATE.format(file=file, sample=sample))
            # add hap tracks
            file = f"bb/hap_differences.bb"
            trackDb.write(HAP_TEMPLATE.format(file=file, sample=sample))
            file = "bb/FDR-wide-peaks.bb"
            trackDb.write(
                BB_TEMPLATE.format(file=file, name="FDR-wide-peaks", sample=sample)
            )

        # add percent accessible tracks
        file = f"bw/{hap}.percent.accessible.bw"
        if hap == "all":
            color = "0,0,0"
            trackDb.write(PER_ACC_COMP.format(sample=sample))
            trackDb.write(FIRE_SCORE_COMP.format(sample=sample, file=f"bw/score.bw"))
        elif hap == "hap1":
            color = "0,0,255"
        elif hap == "hap2":
            color = "255,0,0"

        if hap != "unk":
            viz = "full" if hap != "all" else "hide"
            trackDb.write(
                PER_ACC_TEMPLATE.format(
                    sample=sample, hap=hap, file=file, color=color, viz=viz
                )
            )
            zhap = "" if hap == "all" else f"_{hap}".replace("hap", "H")

            trackDb.write(
                FIRE_SCORE.format(
                    sample=sample,
                    hap=hap,
                    file=f"bw/score{zhap}.bw",
                    viz=viz,
                    color=color,
                )
            )

        # bin files
        if False:
            max_coverage = ave_coverage * 3 * np.sqrt(ave_coverage)
            if hap != "all":
                trackDb.write(TRACK_COMP.format(sample=sample, hap=hap))
                viz = "dense"
                for i in range(max_bins):
                    if hap == "all":
                        continue
                    if i >= max_coverage / 2 and hap != "all" and hap != "unk":
                        continue
                    elif i >= max_coverage:
                        continue
                    trackDb.write(
                        SUB_COMP_TRACK.format(i=i + 1, viz=viz, sample=sample, hap=hap)
                    )
        # new bin files
        if hap == "all":
            for z in ["H1", "H2", "UNK"]:
                trackDb.write(DECORATED.format(sample=sample, hap=z))

    # FDR scores
    trackDb.write(
        FIRE_SCORE_AND_FDR.format(
            sample=sample,
            fdr=f"bw/log_FDR.bw",
            score=f"bw/score.bw",
            y_line=-10 * np.log10(0.05),
        )
    )

    # done with track db
    trackDb.close()


def main(
    *,
    trackhub_dir: Optional[Path] = None,
    reference: Optional[str] = None,
    sample: Optional[str] = None,
    max_bins: Optional[int] = None,
    average_coverage: Optional[int] = 60,
    verbose: int = 0,
):
    """
    Author Mitchell R. Vollger
    """
    logger = logging.getLogger()
    log_format = "[%(levelname)s][Time elapsed (ms) %(relativeCreated)d]: %(message)s"
    log_level = 10 * (3 - verbose)
    logging.basicConfig(format=log_format)
    logger.setLevel(log_level)
    generate_trackhub(trackhub_dir, reference, sample, max_bins, average_coverage)
    return 0


if __name__ == "__main__":
    defopt.run(main, show_types=True, version="0.0.1")
