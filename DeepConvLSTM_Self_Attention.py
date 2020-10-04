import os
import random
import numpy as np
import itertools as it
import tensorflow as tf
import sklearn as skl
from tensorflow.keras.callbacks import LearningRateScheduler, EarlyStopping
from tensorflow.keras.models import load_model
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, LSTM, Conv1D, Input
from tensorflow import keras
from tensorflow.keras import backend as K


# Sliding window length that segments the data
SLIDING_WINDOW_LENGTH = 60

# Batch Size
BATCH_SIZE = 128

# Number of filters in the convolutional layers
NUM_FILTERS = 64

# Size of the filters in the convolutional layers
FILTER_SIZE = 1

# Number of unit in the long short-term recurrent layers
NUM_UNITS_LSTM = 120

# Number of units in the self attention mechanism
ATTENTION_UNITS = 60

# The local width of the attention mechanism
ATTENTION_WIDTH = 10

# Number of epochs to train our model
EPOCHS = 20

# Const number that defines the training learning rate, or how quickly the models converges to a solution
LEARNING_RATE = 0.0001

# The number of epochs until the learning rate is exponentially decreased
LR_EPOCHS = 7

# The seed that is used to set the random number generator
SEED = 0

# The const dataset and directory paths
PASSIVE_DATA_PATH = os.path.join('Dataset', 'Processed', 'Passive', 'passive-dataset.csv')
NPY_PASSIVE_DATA_PATH = os.path.join('Dataset', 'Processed', 'Passive', 'passive-dataset.npy')
AGGRESSIVE_DATA_PATH = os.path.join('Dataset', 'Processed', 'Aggressive', 'aggressive-dataset.csv')
NPY_AGGRESSIVE_DATA_PATH = os.path.join('Dataset', 'Processed', 'Aggressive', 'aggressive-dataset.npy')
MODEL_SAVE_DIR = os.path.join('Saved_Models')


class SeqSelfAttention(keras.layers.Layer):
    ATTENTION_TYPE_ADD = 'additive'
    ATTENTION_TYPE_MUL = 'multiplicative'
    def __init__(self,
                 units=32,
                 attention_width=None,
                 attention_type=ATTENTION_TYPE_ADD,
                 return_attention=False,
                 history_only=False,
                 kernel_initializer='glorot_normal',
                 bias_initializer='zeros',
                 kernel_regularizer=None,
                 bias_regularizer=None,
                 kernel_constraint=None,
                 bias_constraint=None,
                 use_additive_bias=True,
                 use_attention_bias=True,
                 attention_activation=None,
                 attention_regularizer_weight=0.0,
                 **kwargs):
        """Layer initialization.
        For additive attention, see: https://arxiv.org/pdf/1806.01264.pdf
        :param units: The dimension of the vectors that used to calculate the attention weights.
        :param attention_width: The width of local attention.
        :param attention_type: 'additive' or 'multiplicative'.
        :param return_attention: Whether to return the attention weights for visualization.
        :param history_only: Only use historical pieces of data.
        :param kernel_initializer: The initializer for weight matrices.
        :param bias_initializer: The initializer for biases.
        :param kernel_regularizer: The regularization for weight matrices.
        :param bias_regularizer: The regularization for biases.
        :param kernel_constraint: The constraint for weight matrices.
        :param bias_constraint: The constraint for biases.
        :param use_additive_bias: Whether to use bias while calculating the relevance of inputs features
                                  in additive mode.
        :param use_attention_bias: Whether to use bias while calculating the weights of attention.
        :param attention_activation: The activation used for calculating the weights of attention.
        :param attention_regularizer_weight: The weights of attention regularizer.
        :param kwargs: Parameters for parent class.
        """
        super(SeqSelfAttention, self).__init__(**kwargs)
        self.supports_masking = True
        self.units = units
        self.attention_width = attention_width
        self.attention_type = attention_type
        self.return_attention = return_attention
        self.history_only = history_only
        if history_only and attention_width is None:
            self.attention_width = int(1e9)

        self.use_additive_bias = use_additive_bias
        self.use_attention_bias = use_attention_bias
        self.kernel_initializer = keras.initializers.get(kernel_initializer)
        self.bias_initializer = keras.initializers.get(bias_initializer)
        self.kernel_regularizer = keras.regularizers.get(kernel_regularizer)
        self.bias_regularizer = keras.regularizers.get(bias_regularizer)
        self.kernel_constraint = keras.constraints.get(kernel_constraint)
        self.bias_constraint = keras.constraints.get(bias_constraint)
        self.attention_activation = keras.activations.get(attention_activation)
        self.attention_regularizer_weight = attention_regularizer_weight
        self._backend = keras.backend.backend()

        if attention_type == SeqSelfAttention.ATTENTION_TYPE_ADD:
            self.Wx, self.Wt, self.bh = None, None, None
            self.Wa, self.ba = None, None
        elif attention_type == SeqSelfAttention.ATTENTION_TYPE_MUL:
            self.Wa, self.ba = None, None
        else:
            raise NotImplementedError('No implementation for attention type : ' + attention_type)

    def get_config(self):
        config = {
            'units': self.units,
            'attention_width': self.attention_width,
            'attention_type': self.attention_type,
            'return_attention': self.return_attention,
            'history_only': self.history_only,
            'use_additive_bias': self.use_additive_bias,
            'use_attention_bias': self.use_attention_bias,
            'kernel_initializer': keras.initializers.serialize(self.kernel_initializer),
            'bias_initializer': keras.initializers.serialize(self.bias_initializer),
            'kernel_regularizer': keras.regularizers.serialize(self.kernel_regularizer),
            'bias_regularizer': keras.regularizers.serialize(self.bias_regularizer),
            'kernel_constraint': keras.constraints.serialize(self.kernel_constraint),
            'bias_constraint': keras.constraints.serialize(self.bias_constraint),
            'attention_activation': keras.activations.serialize(self.attention_activation),
            'attention_regularizer_weight': self.attention_regularizer_weight,
        }
        base_config = super(SeqSelfAttention, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))

    def build(self, input_shape):
        if self.attention_type == SeqSelfAttention.ATTENTION_TYPE_ADD:
            self._build_additive_attention(input_shape)
        elif self.attention_type == SeqSelfAttention.ATTENTION_TYPE_MUL:
            self._build_multiplicative_attention(input_shape)
        super(SeqSelfAttention, self).build(input_shape)

    def _build_additive_attention(self, input_shape):
        feature_dim = int(input_shape[2])

        self.Wt = self.add_weight(shape=(feature_dim, self.units),
                                  name='{}_Add_Wt'.format(self.name),
                                  initializer=self.kernel_initializer,
                                  regularizer=self.kernel_regularizer,
                                  constraint=self.kernel_constraint)
        self.Wx = self.add_weight(shape=(feature_dim, self.units),
                                  name='{}_Add_Wx'.format(self.name),
                                  initializer=self.kernel_initializer,
                                  regularizer=self.kernel_regularizer,
                                  constraint=self.kernel_constraint)
        if self.use_additive_bias:
            self.bh = self.add_weight(shape=(self.units,),
                                      name='{}_Add_bh'.format(self.name),
                                      initializer=self.bias_initializer,
                                      regularizer=self.bias_regularizer,
                                      constraint=self.bias_constraint)

        self.Wa = self.add_weight(shape=(self.units, 1),
                                  name='{}_Add_Wa'.format(self.name),
                                  initializer=self.kernel_initializer,
                                  regularizer=self.kernel_regularizer,
                                  constraint=self.kernel_constraint)
        if self.use_attention_bias:
            self.ba = self.add_weight(shape=(1,),
                                      name='{}_Add_ba'.format(self.name),
                                      initializer=self.bias_initializer,
                                      regularizer=self.bias_regularizer,
                                      constraint=self.bias_constraint)

    def _build_multiplicative_attention(self, input_shape):
        feature_dim = int(input_shape[2])

        self.Wa = self.add_weight(shape=(feature_dim, feature_dim),
                                  name='{}_Mul_Wa'.format(self.name),
                                  initializer=self.kernel_initializer,
                                  regularizer=self.kernel_regularizer,
                                  constraint=self.kernel_constraint)
        if self.use_attention_bias:
            self.ba = self.add_weight(shape=(1,),
                                      name='{}_Mul_ba'.format(self.name),
                                      initializer=self.bias_initializer,
                                      regularizer=self.bias_regularizer,
                                      constraint=self.bias_constraint)

    def call(self, inputs, mask=None, **kwargs):
        input_len = K.shape(inputs)[1]

        if self.attention_type == SeqSelfAttention.ATTENTION_TYPE_ADD:
            e = self._call_additive_emission(inputs)
        elif self.attention_type == SeqSelfAttention.ATTENTION_TYPE_MUL:
            e = self._call_multiplicative_emission(inputs)

        if self.attention_activation is not None:
            e = self.attention_activation(e)
        if self.attention_width is not None:
            if self.history_only:
                lower = K.arange(0, input_len) - (self.attention_width - 1)
            else:
                lower = K.arange(0, input_len) - self.attention_width // 2
            lower = K.expand_dims(lower, axis=-1)
            upper = lower + self.attention_width
            indices = K.expand_dims(K.arange(0, input_len), axis=0)
            e -= 10000.0 * (1.0 - K.cast(lower <= indices, K.floatx()) * K.cast(indices < upper, K.floatx()))
        if mask is not None:
            mask = K.expand_dims(K.cast(mask, K.floatx()), axis=-1)
            e -= 10000.0 * ((1.0 - mask) * (1.0 - K.permute_dimensions(mask, (0, 2, 1))))

        # a_{t} = \text{softmax}(e_t)
        e = K.exp(e - K.max(e, axis=-1, keepdims=True))
        a = e / K.sum(e, axis=-1, keepdims=True)

        # l_t = \sum_{t'} a_{t, t'} x_{t'}
        v = K.batch_dot(a, inputs)
        if self.attention_regularizer_weight > 0.0:
            self.add_loss(self._attention_regularizer(a))

        if self.return_attention:
            return [v, a]
        return v

    def _call_additive_emission(self, inputs):
        input_shape = K.shape(inputs)
        batch_size, input_len = input_shape[0], input_shape[1]

        # h_{t, t'} = \tanh(x_t^T W_t + x_{t'}^T W_x + b_h)
        q = K.expand_dims(K.dot(inputs, self.Wt), 2)
        k = K.expand_dims(K.dot(inputs, self.Wx), 1)
        if self.use_additive_bias:
            h = K.tanh(q + k + self.bh)
        else:
            h = K.tanh(q + k)

        # e_{t, t'} = W_a h_{t, t'} + b_a
        if self.use_attention_bias:
            e = K.reshape(K.dot(h, self.Wa) + self.ba, (batch_size, input_len, input_len))
        else:
            e = K.reshape(K.dot(h, self.Wa), (batch_size, input_len, input_len))
        return e

    def _call_multiplicative_emission(self, inputs):
        # e_{t, t'} = x_t^T W_a x_{t'} + b_a
        e = K.batch_dot(K.dot(inputs, self.Wa), K.permute_dimensions(inputs, (0, 2, 1)))
        if self.use_attention_bias:
            e += self.ba[0]
        return e

    def compute_output_shape(self, input_shape):
        output_shape = input_shape
        if self.return_attention:
            attention_shape = (input_shape[0], output_shape[1], input_shape[1])
            return [output_shape, attention_shape]
        return output_shape

    def compute_mask(self, inputs, mask=None):
        if self.return_attention:
            return [mask, None]
        return mask

    def _attention_regularizer(self, attention):
        batch_size = K.cast(K.shape(attention)[0], K.floatx())
        input_len = K.shape(attention)[-1]
        indices = K.expand_dims(K.arange(0, input_len), axis=0)
        diagonal = K.expand_dims(K.arange(0, input_len), axis=-1)
        eye = K.cast(K.equal(indices, diagonal), K.floatx())
        return self.attention_regularizer_weight * K.sum(K.square(K.batch_dot(
            attention,
            K.permute_dimensions(attention, (0, 2, 1))) - eye)) / batch_size

    @staticmethod
    def get_custom_objects():
        return {'SeqSelfAttention': SeqSelfAttention}


def deep_conv_lstm_self_attention():
    """
    This function defines a DeepConvLSTM with a Self Attention mechanism model.
    :return: DeepConvLSTM-SelfAttention model.
    """
    # Input shape is num of time steps * features
    input_layer = Input(shape=(SLIDING_WINDOW_LENGTH, 10), batch_size=BATCH_SIZE)
    conv = Conv1D(NUM_FILTERS, FILTER_SIZE, padding='same', activation='relu', input_shape=(SLIDING_WINDOW_LENGTH, 10))(input_layer)
    conv2 = Conv1D(NUM_FILTERS, FILTER_SIZE, padding='same', activation='relu')(conv)
    conv3 = Conv1D(NUM_FILTERS, FILTER_SIZE, padding='same', activation='relu')(conv2)
    lstm = LSTM(NUM_UNITS_LSTM, dropout=0.3, activation='tanh', return_sequences=True)(conv3)
    attention = SeqSelfAttention(ATTENTION_UNITS, attention_width=ATTENTION_WIDTH, attention_activation='tanh')
    attention_out = attention(lstm)
    dense = Dense(1024, activation='relu')(attention_out)
    output_layer = Dense(1, activation='sigmoid')(dense)
    model_ = Model(inputs=input_layer, outputs=output_layer)
    print(model_.summary())
    return model_


def learning_scheduler(epoch):
    """
    This function keeps the learning rate at [LEARNING_RATE] for the first [LR_EPOCHS] epochs
    and decreases it exponentially after that.
    :return: The learning rate.
    """
    if epoch <= LR_EPOCHS:
        lr = LEARNING_RATE
        print('LR IS:', lr)
        return float(lr)
    else:
        lr = LEARNING_RATE * np.exp(0.1 * (LR_EPOCHS - epoch))
        print('LR IS:', lr)
        return float(lr)


def sliding_window(data, length, step=1):
    """
    This function splits our processed dataset into windows of size [SLIDING_WINDOW_LENGTH].
    :return: NumPy array that contains the windowed dataset.
    """
    streams = it.tee(data, length)
    a = zip(*[it.islice(stream, i, None, step*length) for stream, i in zip(streams, it.count(step=step))])
    b = list(a)
    return np.asarray(b)


if __name__ == '__main__':
    print("\nTensorflow version: ", tf.__version__)
    print("Eager mode: ", tf.executing_eagerly())
    print("GPU is", "available!" if tf.config.experimental.list_physical_devices('GPU') else "not available!\n")
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    # Check if model save directory exists, else mkdir
    if not os.path.exists(os.path.join(MODEL_SAVE_DIR)):
        os.mkdir(os.path.join(MODEL_SAVE_DIR))

    # Set random seeds for libraries
    random.seed(SEED)
    np.random.seed(SEED)
    tf.random.set_seed(SEED)

    passive = []
    aggressive = []

    # Check if passive numpy saves exist, if so load .npy, else read in .csv
    if os.path.exists(os.path.join(NPY_PASSIVE_DATA_PATH)):
        print('Reading in saved passive NumPy dataset...')
        passive = np.load(NPY_PASSIVE_DATA_PATH)
    else:
        print('No saved passive dataset, reading in and processing new data.')
        passive = np.genfromtxt(PASSIVE_DATA_PATH, delimiter=',', skip_header=1, dtype=int)
        np.save(NPY_PASSIVE_DATA_PATH, passive)

    # Check if aggressive numpy saves exist, if so load .npy, else read in .csv
    if os.path.exists(os.path.join(NPY_AGGRESSIVE_DATA_PATH)):
        print('Reading in saved aggressive NumPy dataset...')
        aggressive = np.load(NPY_AGGRESSIVE_DATA_PATH)
    else:
        print('No saved aggressive dataset, reading in and processing new data.')
        aggressive = np.genfromtxt(AGGRESSIVE_DATA_PATH, delimiter=',', skip_header=1, dtype=int)
        np.save(NPY_AGGRESSIVE_DATA_PATH, aggressive)

    # Extract labels
    passive_labels = passive[:, -1]
    aggressive_labels = aggressive[:, -1]

    # Generate sliding windows on passive and aggressive
    passive_ = sliding_window(passive[:, :-1], SLIDING_WINDOW_LENGTH)
    passive_labels_ = sliding_window(passive_labels, SLIDING_WINDOW_LENGTH)
    aggressive_ = sliding_window(aggressive[:, :-1], SLIDING_WINDOW_LENGTH)
    aggressive_labels_ = sliding_window(aggressive_labels, SLIDING_WINDOW_LENGTH)

    # Concatenate and then shuffle the dataset windows around
    X = np.concatenate((passive_, aggressive_))
    y = np.concatenate((passive_labels_, aggressive_labels_))
    X_, y_ = skl.utils.shuffle(X, y, random_state=SEED)

    # Split into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X_, y_, test_size=0.2, random_state=SEED)

    # Prompt the user to supply 'y' or 'n' to retrain model
    retrainCheck = input('Do you want to train a new model (y/n)? ')
    if retrainCheck == 'y':
        # Initialise our DeepConvLSTM with Self-Attention Mechanism model
        model = deep_conv_lstm_self_attention()

        # Sets our callback for the learning rate scheduler
        lrs = LearningRateScheduler(learning_scheduler)

        # Sets our callback for the early stopper
        es = EarlyStopping(monitor='loss', min_delta=0.005, patience=1, verbose=0, mode='min',
                           restore_best_weights=False, baseline=None)

        # Print the shapes and number of training instances and testing instances
        print('Number of training instances:', X_train.shape[0])
        print('Number of test instances:    ', X_test.shape[0])

        # X_train, y_train, X_test, and y_test are all numpy arrays
        print('X_train.shape =', X_train.shape)
        print('y_train.shape =', y_train.shape)
        print('X_test.shape =', X_test.shape)
        print('y_test.shape =', y_test.shape)

        # Fit the model to the training data
        optimizer = tf.keras.optimizers.Adam()
        model.compile(optimizer=optimizer, loss='binary_crossentropy', metrics=['accuracy'])
        model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, validation_split=0.05, callbacks=[lrs, es])

        # Evaluate the model
        y_pred_score = model.evaluate(X_test, y_test, batch_size=BATCH_SIZE, verbose=0)

        # Let's take a look at our model's loss and accuracy score
        print("DeepConvLSTM-Self-Attention accuracy: ", y_pred_score[1])
        print("DeepConvLSTM-Self-Attention loss: ", y_pred_score[0])

        # Check to see if we have a previous best model saved
        if os.path.exists(os.path.join(MODEL_SAVE_DIR, 'best_model.h5')):
            # Load our previous best model
            savedModel = load_model(os.path.join(MODEL_SAVE_DIR, 'best_model.h5'),
                                    custom_objects={'SeqSelfAttention': SeqSelfAttention})

            # Evaluate our old model
            try:
                savedModelScore = savedModel.evaluate(X_test, y_test, batch_size=BATCH_SIZE, verbose=0)
            except:
                print('The previously saved model expects different sliding window lengths.')
                print('Please remove saved model if you wish to train on a different sliding window length.')
                quit()

            # If it is better (based on accuracy), then we should overwrite our previous best model
            if y_pred_score[1] > savedModelScore[1]:
                model.save(os.path.join(MODEL_SAVE_DIR, 'best_model.h5'))
                print('New best model saved!')
        # If no previous best model, then save this new model as our best
        else:
            model.save(os.path.join(MODEL_SAVE_DIR, 'best_model.h5'))
            print('Saved model!')
    elif retrainCheck == 'n':
        # Check to see if we have a previous best model saved
        if os.path.exists(os.path.join(MODEL_SAVE_DIR, 'best_model.h5')):
            # Load in our saved model, custom_objects must be defined to load it correctly
            model = load_model(os.path.join(MODEL_SAVE_DIR, 'best_model.h5'),
                               custom_objects={'SeqSelfAttention': SeqSelfAttention})
            print(model.summary())

            # Evaluate the model
            y_pred_score = model.evaluate(X_test, y_test, batch_size=BATCH_SIZE, verbose=0)

            # Let's take a look at our model's loss and accuracy score
            print("DeepConvLSTM-Self-Attention accuracy: ", y_pred_score[1])
            print("DeepConvLSTM-Self-Attention loss: ", y_pred_score[0])
        # Prompt user that there is no previously saved model.
        else:
            print('No previous model has been saved. Please train a new model.')