"""Defines a logistic regression model to serve as a baseline"""

import tensorflow as tf
from tensorflow import math as tfm

from .inf_vi_ybar import (sensitive_prediction, construct_input, debiasing_params_target_rate,
                          debiasing_params_target_tpr)

tf.compat.v1.app.flags.DEFINE_boolean('use_bias', True,
                                      'If True, logistic regression will use a bias')
tf.compat.v1.app.flags.DEFINE_float(
    'lr_l2_kernel_factor', 0.1,
    'Weight of the regularization loss for the kernel of logistic regression')
tf.compat.v1.app.flags.DEFINE_float(
    'lr_l2_bias_factor', 0.1,
    'Weight of the regularization loss for the bias of logistic regression')


class LogReg(tf.keras.Model):
    """Simple logistic regression model"""
    def __init__(self, args, _, output_dim, *__, **kwargs):
        super().__init__()
        self.args = args
        # create the logistic regression model
        # this is just a single layer neural network. we use no activation function here,
        # but we use `sigmoid_cross_entropy_with_logits` for the loss function which means
        # there is implicitly the logistic function as the activation function.
        self._model = tf.keras.layers.Dense(
            output_dim, activation=None, use_bias=args['use_bias'],
            kernel_regularizer=tf.keras.regularizers.l2(args['lr_l2_kernel_factor']),
            bias_regularizer=tf.keras.regularizers.l2(args['lr_l2_bias_factor'])
        )

    def inference(self, features, outputs, _):
        """Standard logistic regression loss"""
        inputs = self._get_inputs(features)
        logits = self._model(inputs)
        # this loss function implicitly uses the logistic function on the output of the one layer
        log_cond_prob = -tf.nn.sigmoid_cross_entropy_with_logits(labels=outputs, logits=logits)
        l2_loss = self._l2_loss()
        regr_loss = -tf.reduce_mean(input_tensor=tf.squeeze(log_cond_prob), axis=-1)  # regression loss
        return {'loss': regr_loss + l2_loss, 'regr_loss': regr_loss, 'l2_loss': l2_loss}

    def prediction(self, test_inputs):
        """Make a prediction"""
        return sensitive_prediction(self, test_inputs, self.args)

    def call(self, inputs, **_):
        pred = tf.nn.sigmoid(self._model(inputs))
        return pred, tf.zeros_like(pred)

    def _l2_loss(self):
        return tf.add_n(self._model.losses)  # L2 regularization loss

    def _get_inputs(self, features):
        return construct_input(features, self.args)


class FairLogReg(LogReg):
    """Fair logistic regression for demographic parity"""
    def inference(self, features, outputs, is_train):
        """Inference for targeting ybar"""
        if not is_train:
            return super().inference(features, outputs, is_train)
        sens_attr = tf.cast(tf.squeeze(features['sensitive'], -1), dtype=tf.int32)
        out_int = tf.cast(tf.squeeze(outputs, -1), dtype=tf.int32)
        # output
        logits = tf.squeeze(self._model(self._get_inputs(features)), axis=-1)
        # log likelihood for y=1
        log_lik1 = tfm.log_sigmoid(logits)
        # log likelihood for y=0
        log_lik0 = tfm.log_sigmoid(-logits)
        log_lik = tf.stack((log_lik0, log_lik1), axis=-1)
        log_debias = self._log_debiasing_parameters()
        # `log_debias` has the shape (y, s, y'). we stack output and sensitive to (batch_size, 2)
        # then we use the last 2 values of that as indices for `log_debias`
        # shape of log_debias_per_example: (batch_size, output_dim, 2)
        log_debias_per_example = tf.gather_nd(log_debias, tf.stack((out_int, sens_attr), axis=-1))
        weighted_log_lik = log_debias_per_example + log_lik
        # logsumexp is numerically stable
        log_cond_prob = tf.reduce_logsumexp(input_tensor=weighted_log_lik, axis=-1)
        regr_loss = -tf.reduce_mean(input_tensor=log_cond_prob)
        l2_loss = self._l2_loss()
        return {'loss': regr_loss + l2_loss, 'regr_loss': regr_loss, 'l2_loss': l2_loss}

    def _log_debiasing_parameters(self):
        return debiasing_params_target_rate(self.args)


class EqOddsLogReg(FairLogReg):
    """Fair logistic regression for equalized odds (or equality of opportunity)"""
    def _log_debiasing_parameters(self):
        return debiasing_params_target_tpr(self.args)
