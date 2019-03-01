import scipy.misc
import numpy as np
import os
import itertools
from glob import glob
import imageio

import tensorflow as tf
import tensorflow.contrib.slim as slim

from inception_score import calculate_inception_score

class EasyDict(dict):
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs)
    def __getattr__(self, name): return self[name]
    def __setattr__(self, name, value): self[name] = value
    def __delattr__(self, name): del self[name]

class ImageData:

    def __init__(self, load_size, channels, custom_dataset):
        self.load_size = load_size
        self.channels = channels
        self.custom_dataset = custom_dataset

    def image_processing(self, filename):

        if not self.custom_dataset :
            x_decode = filename
        else :
            x = tf.read_file(filename)
            x_decode = tf.image.decode_jpeg(x, channels=self.channels)

        img = tf.image.resize_images(x_decode, [self.load_size, self.load_size])
        img = tf.cast(img, tf.float32) / 127.5 - 1

        return img


def load_mnist():
    from keras.datasets import mnist
    (train_data, train_labels), (test_data, test_labels) = mnist.load_data()
    x = np.concatenate((train_data, test_data), axis=0)
    x = np.expand_dims(x, axis=-1)

    return x

def load_cifar10():
    from keras.datasets import cifar10
    (train_data, train_labels), (test_data, test_labels) = cifar10.load_data()
    x = np.concatenate((train_data, test_data), axis=0)

    return x

def load_data(dataset_name) :
    if dataset_name == 'mnist' :
        x = load_mnist()
    elif dataset_name == 'cifar10' :
        x = load_cifar10()
    else :

        x = glob(os.path.join("./dataset", dataset_name, '*.*'))

    return x


def preprocessing(x, size):
    x = scipy.misc.imread(x, mode='RGB')
    x = scipy.misc.imresize(x, [size, size])
    x = normalize(x)
    return x

def normalize(x) :
    return x/127.5 - 1



def save_predictions(args, result_dir, predictions, epoch, total_steps):

    image_frame_dim = int(np.floor(np.sqrt(args.sample_num)))
    samples = []

    try:
        for ct, i in enumerate(predictions):
            if ct >= args.sample_num:
                break
            samples.append(i['fake_image'])
    
    except tf.errors.OutOfRangeError:
        pass

    if len(samples) == 0:
        tf.logging.warning(f"No predictions returned from TensorFlow in epoch {epoch}")
        return

    else:
        tf.logging.info(f"Saving grid of {len(samples)} predictions")

    samples = np.array(samples)
    grid_samples = samples[:image_frame_dim * image_frame_dim, :, :, :]

    for filename in ['epoch%02d' % epoch + '_sample.png', 'latest_sample.png']:
        file_path = os.path.join(result_dir, filename)
        with tf.gfile.Open(file_path, 'wb') as file:
            grid_image = merge(inverse_transform(grid_samples), [image_frame_dim, image_frame_dim])
            imageio.imwrite(file, grid_image, format="png")

    inception_score = calculate_inception_score(samples)

    file_path = os.path.join(result_dir, "eval.txt")

    with tf.gfile.Open(file_path, 'a') as file:
        file.write(f"Step {total_steps}\t inception_score={inception_score}\n")





def save_evaluation(args, result_dir, evaluation, epoch, total_steps):
    file_path = os.path.join(result_dir, "eval.txt")

    with tf.gfile.Open(file_path, 'a') as file:
        file.write(f"Step {total_steps}\t {evaluation}\n")



def merge(images, size):
    h, w = images.shape[1], images.shape[2]
    if (images.shape[3] in (3,4)):
        c = images.shape[3]
        img = np.zeros((h * size[0], w * size[1], c))
        for idx, image in enumerate(images):
            i = idx % size[1]
            j = idx // size[1]
            img[j * h:j * h + h, i * w:i * w + w, :] = image
        return img
    elif images.shape[3]==1:
        img = np.zeros((h * size[0], w * size[1]))
        for idx, image in enumerate(images):
            i = idx % size[1]
            j = idx // size[1]
            img[j * h:j * h + h, i * w:i * w + w] = image[:,:,0]
        return img
    else:
        raise ValueError('in merge(images,size) images parameter ''must have dimensions: HxW or HxWx3 or HxWx4')


def inverse_transform(images):
    return (images+1.)/2.


def show_all_variables():
    model_vars = tf.trainable_variables()
    slim.model_analyzer.analyze_vars(model_vars, print_info=True)

def str2bool(x):
    return x.lower() in ('true')

##################################################################################
# Regularization
##################################################################################

def orthogonal_regularizer(scale) :
    """ Defining the Orthogonal regularizer and return the function at last to be used in Conv layer as kernel regularizer"""

    def ortho_reg(w) :
        """ Reshaping the matrxi in to 2D tensor for enforcing orthogonality"""
        _, _, _, c = w.get_shape().as_list()

        w = tf.reshape(w, [-1, c])

        """ Declaring a Identity Tensor of appropriate size"""
        identity = tf.eye(c)

        """ Regularizer Wt*W - I """
        w_transpose = tf.transpose(w)
        w_mul = tf.matmul(w_transpose, w)
        reg = tf.subtract(w_mul, identity)

        """Calculating the Loss Obtained"""
        ortho_loss = tf.nn.l2_loss(reg)

        return scale * ortho_loss

    return ortho_reg

def orthogonal_regularizer_fully(scale) :
    """ Defining the Orthogonal regularizer and return the function at last to be used in Fully Connected Layer """

    def ortho_reg_fully(w) :
        """ Reshaping the matrix in to 2D tensor for enforcing orthogonality"""
        _, c = w.get_shape().as_list()

        """Declaring a Identity Tensor of appropriate size"""
        identity = tf.eye(c)
        w_transpose = tf.transpose(w)
        w_mul = tf.matmul(w_transpose, w)
        reg = tf.subtract(w_mul, identity)

        """ Calculating the Loss """
        ortho_loss = tf.nn.l2_loss(reg)

        return scale * ortho_loss

    return ortho_reg_fully