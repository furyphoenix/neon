#!/usr/bin/env python
# ----------------------------------------------------------------------------
# Copyright 2015 Nervana Systems Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ----------------------------------------------------------------------------
"""
Example that trains an LSTM or GRU based recurrent networks.
The dataset uses Penn Treebank dataset parsing on word-level.

Reference:
    Recurrent Neural Network Regularization `[Zaremba2015]`_
    Generating sequences with recurrent neural networks `[Graves2014]`_
.. _[Zaremba2015]: http://arxiv.org/pdf/1409.2329v5.pdf
.. _[Graves2014]: http://arxiv.org/pdf/1308.0850.pdf
"""

from neon.backends import gen_backend
from neon.data import Text
from neon.data import load_text
from neon.initializers import Uniform
from neon.layers import GeneralizedCost, LSTM, Affine, GRU
from neon.models import Model
from neon.optimizers import RMSProp
from neon.transforms import Logistic, Tanh, Softmax, CrossEntropyMulti
from neon.callbacks.callbacks import Callbacks
from neon.util.argparser import NeonArgparser, extract_valid_args

# parse the command line arguments
parser = NeonArgparser(__doc__)
parser.add_argument('--rlayer_type', default='lstm', choices=['gru', 'lstm'],
                    help='type of recurrent layer to use (gru or lstm)')
args = parser.parse_args(gen_be=False)

# hyperparameters from the reference
args.batch_size = 20
time_steps = 20
hidden_size = 200
clip_gradients = True
gradient_limit = 5

# setup backend
be = gen_backend(**extract_valid_args(args, gen_backend))

# download penn treebank
train_path = load_text('ptb-train', path=args.data_dir)
valid_path = load_text('ptb-valid', path=args.data_dir)

# load data and parse on word-level
# a Text object can take a given tokenizer, for word-level parsing, it is str.split
# a user can pass in a custom-defined tokenzier as well
train_set = Text(time_steps, train_path, tokenizer=str.split)
valid_set = Text(time_steps, valid_path, vocab=train_set.vocab, tokenizer=str.split)

# weight initialization
init = Uniform(low=-0.08, high=0.08)

# model initialization
if args.rlayer_type == 'lstm':
    rlayer1 = LSTM(hidden_size, init, activation=Logistic(), gate_activation=Tanh())
    rlayer2 = LSTM(hidden_size, init, activation=Logistic(), gate_activation=Tanh())
else:
    rlayer1 = GRU(hidden_size, init, activation=Tanh(), gate_activation=Logistic())
    rlayer2 = GRU(hidden_size, init, activation=Tanh(), gate_activation=Logistic())

layers = [rlayer1,
          rlayer2,
          Affine(len(train_set.vocab), init, bias=init, activation=Softmax())]

cost = GeneralizedCost(costfunc=CrossEntropyMulti(usebits=True))

model = Model(layers=layers)

optimizer = RMSProp(clip_gradients=clip_gradients, gradient_limit=gradient_limit,
                    stochastic_round=args.rounding)

# configure callbacks
callbacks = Callbacks(model, train_set, eval_set=valid_set, **args.callback_args)

# train model
model.fit(train_set, optimizer=optimizer, num_epochs=args.epochs, cost=cost, callbacks=callbacks)
