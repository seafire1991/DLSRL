import json
from argparse import Namespace
import tensorflow as tf
import time
from tfvis import Timeline

from data_utils import get_data
from batcher import Batcher
from model import Model

CONFIG_FILE_PATH = 'config.json'
TRAIN_DATA_PATH = 'data/conll05.train.txt'
DEV_DATA_PATH =  'data/conll05.dev.txt'
VOCAB_PATH = None
LABEL_PATH = None

EVALUATE_WHICH = ['train', 'dev']
LOSS_INTERVAL = 100
TFVIS_PATH = None  #'/home/ph'


def evaluate(which):
    batch_accuracies = []
    for w_ids_batch, p_ids_batch, l_ids_batch in batcher.get_batched_tensors(which=which):
        feed_dict = {model.word_ids: w_ids_batch,
                     model.predicate_ids: p_ids_batch,
                     model.label_ids: l_ids_batch}
        [batch_acc] = sess.run([model.accuracy], feed_dict=feed_dict)
        batch_accuracies.append(batch_acc)
    print('{} accuracy={:.3f}'.format(which, sum(batch_accuracies) / len(batch_accuracies)))


# config
with open(CONFIG_FILE_PATH, 'r') as config_file:
    config = json.load(config_file, object_hook=lambda d: Namespace(**d))
print('///// Configs START')
for k in sorted(config.__dict__):
    v = vars(config)[k]
    print('    {:>20}={:<20}'.format(k, v))
print('///// Configs END')

# data
train_data, dev_data, word_dict, num_labels, embeddings = get_data(
    config, TRAIN_DATA_PATH, DEV_DATA_PATH, VOCAB_PATH, LABEL_PATH)

# model
batcher = Batcher(config, train_data, dev_data)
model = Model(config, embeddings, num_labels)


# profiling
if TFVIS_PATH:
    with tf.train.MonitoredSession() as sess:
        with Timeline() as timeline:
            w_ids_batch, p_ids_batch, l_ids_batch = next(batcher.get_batched_tensors('train'))
            feed_dict = {model.word_ids: w_ids_batch,
                         model.predicate_ids: p_ids_batch,
                         model.label_ids: l_ids_batch}
            sess.run(model.update, feed_dict=feed_dict, **timeline.kwargs)
            print('visualizing timeline at {}...'.format(TFVIS_PATH))
            timeline.visualize("{}/profile_num_layers={}.html".format(TFVIS_PATH, config.num_layers))

# train
local_step = 0
global_step = 0
train_loss = 0.0
start = time.time()
with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    for epoch in range(config.max_epochs):

        # eval
        for which in EVALUATE_WHICH:
            evaluate(which)

        # train
        for w_ids_batch, p_ids_batch, l_ids_batch in batcher.get_batched_tensors('train'):
            feed_dict = {model.word_ids: w_ids_batch,
                         model.predicate_ids: p_ids_batch,
                         model.label_ids: l_ids_batch}
            loss, _ = sess.run([model.mean_loss, model.update],
                               feed_dict=feed_dict)
            train_loss += loss
            local_step += 1
            global_step += 1
            if local_step % LOSS_INTERVAL == 0 or local_step == 1:
                print("step {:>6} (global {:>6}): loss={:.3f}, min elapsed={:.3f}".format(
                    local_step, global_step, train_loss / local_step, (time.time() - start) / 60))

        print("Completed Epoch {:3}\n".format(epoch))
        local_step = 0
        train_loss = 0.0






    

