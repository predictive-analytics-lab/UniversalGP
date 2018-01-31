import copy

import tensorflow as tf


def init_list(init, dims):
    def empty_list(dims):
        if not dims:
            return None
        else:
            return [copy.deepcopy(empty_list(dims[1:])) for i in range(dims[0])]

    def fill_list(dims, l):
        if len(dims) == 1:
            for i in range(dims[0]):
                if callable(init):
                    l[i] = init()
                else:
                    l[i] = init
        else:
            for i in range(dims[0]):
                fill_list(dims[1:], l[i])

    l = empty_list(dims)
    fill_list(dims, l)

    return l


def ceil_divide(dividend, divisor):
    return (dividend + divisor - 1) / divisor


def log_cholesky_det(chol):
    return 2 * tf.reduce_sum(tf.log(tf.diag_part(chol)))


def diag_mul(mat1, mat2):
    return tf.reduce_sum(mat1 * tf.transpose(mat2), 1)


def logsumexp(vals, dim=None):
    m = tf.reduce_max(vals, dim)
    if dim is None:
        return m + tf.log(tf.reduce_sum(tf.exp(vals - m), dim))
    else:
        return m + tf.log(tf.reduce_sum(tf.exp(vals - tf.expand_dims(m, dim)), dim))


def mat_square(mat):
    return mat @ tf.transpose(mat)


def tri_vec_shape(N):
    return [N * (N + 1) // 2]


def vec_to_tri(vectors):
    """
    Takes a DxM tensor vectors and maps it to a D x matrix_size x matrix_size
    tensor where the lower triangle of each matrix_size x matrix_size matrix
    is constructed by unpacking each M-vector.
    """
    M = vectors.shape[1].value
    N = int(np.floor(0.5 * np.sqrt(M * 8. + 1) - 0.5))
    assert N * (N + 1) == 2 * M  # check M is a valid triangle number.
    indices = tf.constant(np.stack(np.tril_indices(N)).T, dtype=tf.int32)

    def vec_to_tri_vector(vector):
        return tf.scatter_nd(indices=indices, shape=[N, N], updates=vector)

    return tf.map_fn(vec_to_tri_vector, vectors)


def get_flags():
    flags = tf.app.flags
    FLAGS = flags.FLAGS
    flags.DEFINE_integer('batch_size', 100, 'Batch size.  '
                                           'Must divide evenly into the dataset sizes.')
    flags.DEFINE_float('learning_rate', 0.001, 'Initial learning rate.')
    flags.DEFINE_integer('n_epochs', 10000, 'Number of passes through the data')
    flags.DEFINE_integer('n_inducing', 240, 'Number of inducing points')
    flags.DEFINE_integer('display_step', 500, 'Display progress every FLAGS.display_step iterations')
    flags.DEFINE_integer('mc_train', 100, 'Number of Monte Carlo samples used to compute stochastic gradients')
    flags.DEFINE_integer('mc_test', 100, 'Number of Monte Carlo samples for predictions')
    flags.DEFINE_string('optimizer', "adagrad", 'Optimizer')
    flags.DEFINE_boolean('is_ard', True, 'Using ARD kernel or isotropic')
    flags.DEFINE_float('lengthscale', 10, 'Initial lengthscale')
    flags.DEFINE_integer('var_steps', 50, 'Number of times spent optimizing the variational objective.')
    flags.DEFINE_integer('loocv_steps', 50, 'Number of times spent optimizing the LOOCV objective.')
    flags.DEFINE_float('opt_growth', 0.0, 'Percentage to grow the number of each optimizations.')
    flags.DEFINE_integer('num_components', 1, 'Number of mixture components on posterior')
    flags.DEFINE_string('kernel', 'rbf', 'kernel')
    flags.DEFINE_string('device_name', 'gpu0', 'Device name')
    flags.DEFINE_integer('kernel_degree', 0, 'Degree of arccosine kernel')
    flags.DEFINE_integer('kernel_depth', 1, 'Depth of arcosine kernel')
    flags.DEFINE_boolean('hyper_with_elbo', True, 'Optimize hyperparameters with elbo as well')
    flags.DEFINE_boolean('normalize_features', False, 'Normalizes features')
    flags.DEFINE_boolean('optimize_inducing', True, 'Optimize inducing inputs')
    flags.DEFINE_float('latent_noise', 0.001, 'latent noise for Kernel matrices')
    return FLAGS
