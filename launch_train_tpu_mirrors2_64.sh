#!/bin/bash

nohup pipenv run python3.6 main_tpu.py --use-tpu \
	--train-input-path ../gdrive/My\ Drive/Artificial/images/datasets/mirrors2_4 \
	--eval-input-path ../gdrive/My\ Drive/Artificial/images/datasets/mirrors2_4 \
	--model-dir ../gdrive/My\ Drive/Artificial/images/models \
	--result-dir ../gdrive/My\ Drive/Artificial/images/results \
	--batch-size 256  \
	--ch 64 \
	--self-attn-res 64 \
	--g-lr 0.0001 \
	--d-lr 0.0004 \
	--verbosity INFO \
	--train-examples 1281167 \
	--eval-examples 50000 \
	--tag sagan \
	--tag run-$RANDOM \
	$@ &
	