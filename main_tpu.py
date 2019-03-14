

from comet_ml import Experiment
import tensorflow as tf

from BigGAN import BigGAN
from inception_score import prefetch_inception_model

import argparse
import subprocess
import os.path
import math

import logging
logger = logging.getLogger(__name__)

from utils import *
from input import *
from args  import *


def main():
	args = parse_args()
	setup_logging(args)

	gan = BigGAN(args)

	if args.use_tpu:
		cluster_resolver = tf.contrib.cluster_resolver.TPUClusterResolver(
			tpu=args.tpu_name,
			zone=args.tpu_zone)
		master = cluster_resolver.get_master()
	else:
		master = ''

	tpu_run_config = tf.contrib.tpu.RunConfig(
		master=master,
		evaluation_master=master,
		model_dir=model_dir(args),
		session_config=tf.ConfigProto(
			allow_soft_placement=True, 
			log_device_placement=False),
		tpu_config=tf.contrib.tpu.TPUConfig(args.steps_per_loop,
											args.num_shards),
	)

	tpu_estimator = tf.contrib.tpu.TPUEstimator(
		model_fn=lambda features, labels, mode, params: gan.tpu_model_fn(features, labels, mode, params),
		config = tpu_run_config,
		use_tpu=args.use_tpu,
		train_batch_size=args._batch_size,
		eval_batch_size=args._batch_size,
		predict_batch_size=args._batch_size,
		params=vars(args),
	)

	total_steps = 0

	if args.use_comet:
		experiment = Experiment(api_key=comet_ml_api_key, project_name=comet_ml_project, workspace=comet_ml_workspace)
		experiment.log_parameters(vars(args))
		experiment.add_tags(args.tag)
		experiment.set_name(model_name(args))
	else:
		experiment = None

	prefetch_inception_model()

	train_steps = math.ceil(args.train_examples / args._batch_size)
	eval_steps  = math.ceil(args.eval_examples  / args._batch_size)

	with tf.gfile.Open(os.path.join(suffixed_folder(args, args.result_dir), "eval.txt"), "a") as eval_file:
		for epoch in range(args.epochs):

			logger.info(f"Training epoch {epoch}")
			tpu_estimator.train(input_fn=train_input_fn, steps=train_steps)
			total_steps += train_steps
			
			logger.info(f"Evaluate {epoch}")
			evaluation = tpu_estimator.evaluate(input_fn=eval_input_fn, steps=eval_steps)
			
			if args.use_comet:
				experiment.set_step(total_steps)
				experiment.log_metrics(evaluation)
				
			logger.info(evaluation)
			save_evaluation(args, eval_file, evaluation, epoch, total_steps)

			logger.info(f"Generate predictions {epoch}")
			predictions = tpu_estimator.predict(input_fn=predict_input_fn)
			
			logger.info(f"Save predictions")
			save_predictions(args, suffixed_folder(args, args.result_dir), eval_file, predictions, epoch, total_steps, experiment)




if __name__ == '__main__':
	main()

