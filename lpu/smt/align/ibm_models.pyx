# distutils: language=c++
# -*- coding: utf-8 -*-

# C++ set-up
from libcpp cimport bool

# Standard libraries
import argparse

# 3-rd party library
import numpy as np
cimport numpy as np
from numpy cimport ndarray
from numpy cimport float64_t
from numpy cimport int64_t

# Local libraries

from lpu.common import compat
from lpu.common import environ
from lpu.common import files
from lpu.common import progress

from lpu.common.config cimport Config
from lpu.common.vocab cimport StringEnumerator
from lpu.common import logging

logger = logging.getColorLogger(__name__)
dprint = logger.debug_print

from . ibm_model1 cimport Model1, Model1Trainer
from . ibm_model2 cimport Model2, Model2Trainer

ITERATION_LIMIT = 5
THRESHOLD = 0.001
NBEST = 100

NULL_SYMBOL = '__NULL__'

cdef tuple grid_indices(list x_indices, list y_indices):
    cdef ndarray[int64_t,ndim=2] indices1, indices2
    indices1, indices2 = np.meshgrid(x_indices, y_indices, sparse=True)
    return indices1.T, indices2.T

cdef ndarray[float64_t,ndim=2] sub_matrix(ndarray[float64_t,ndim=2] matrix, list x_indices, list y_indices):
    return matrix[grid_indices(x_indices, y_indices)]

cdef ndarray normalize(ndarray tensor, int axis, ndarray target):
    cdef ndarray positive_indices
    cdef ndarray denom = tensor.sum(axis=axis)
    denom = np.expand_dims(denom, axis=axis)
    denom = np.broadcast_to(denom, tensor[:].shape)
    positive_indices = (denom > 0)
    target[positive_indices] = tensor[positive_indices] / denom[positive_indices]
    return target

cdef class Vocab:
    # imported from "ibm_model1.pxd"
    #cdef StringEnumerator src
    #cdef StringEnumerator trg
    #cdef int max_len_src
    #cdef int max_len_trg

    def __cinit__(self):
        self.init()
    cdef void init(self):
        self.src = StringEnumerator()
        self.trg = StringEnumerator()

    cdef tuple ids_pair_to_str_pair(self, src_ids, trg_ids, bool character_based):
        cdef src_str, trg_str
        if character_based:
            src_str = str.join('', [self.src.id2str(i) for i in src_ids[:-1]])
            trg_str = str.join('', [self.trg.id2str(i) for i in trg_ids])
        else:
            src_str = str.join(' ', [self.src.id2str(i) for i in src_ids[:-1]])
            trg_str = str.join(' ', [self.trg.id2str(i) for i in trg_ids])
        return src_str, trg_str

    cdef list load_sent_pairs(self, str src_path, str trg_path, bool character_based):
        cdef str src_line, trg_line
        cdef list src_words, trg_words
        cdef list src_ids, trg_ids
        cdef list sent_pairs
        cdef str word
        logger.info("loading files: %s %s" % (src_path,trg_path))
        self.src.append(NULL_SYMBOL)
        src_file = progress.FileReader(src_path, 'loading')
        trg_file = files.open(trg_path)
        sent_pairs = []
        dprint(src_file)
        for src_line, trg_line in zip(src_file, trg_file):
            if character_based:
                src_words = list( compat.to_unicode(src_line.strip("\n")) )
                trg_words = list( compat.to_unicode(trg_line.strip("\n")) )
                src_words = list( map(compat.to_str, src_words) )
                trg_words = list( map(compat.to_str, trg_words) )
            else:
                src_words = src_line.strip("\n").split(' ')
                trg_words = trg_line.strip("\n").split(' ')
            src_words = [NULL_SYMBOL] + src_words
            src_ids = [self.src.str2id(word) for word in src_words]
            trg_ids = [self.trg.str2id(word) for word in trg_words]
            sent_pairs.append( (src_ids, trg_ids) )
            self.max_len_src = max(self.max_len_src, len(src_ids))
            self.max_len_trg = max(self.max_len_src, len(trg_ids))
        return sent_pairs

cdef class Model:
    # imported from "ibm_model1.pxd"
    #cdef np.ndarray trans_dist
    #cdef Vocab vocab

    def __cinit__(self):
        dprint("base model cinit")
        self.init()
    cdef inline void init(self):
        self.vocab = Vocab()

    cdef double calc_pair_entropy(self, list src_sent, list trg_sent, bool normalize) except *:
        raise NotImplementedError()

    cdef double calc_entropy(self, list sent_pairs) except *:
        cdef float total_entropy = 0
        logger.info('calculating entropy')
        for i, (src_sent, trg_sent) in enumerate(progress.view(sent_pairs, 'progress')):
            total_entropy += self.calc_pair_entropy(src_sent, trg_sent, True)
        return total_entropy / len(sent_pairs)

    cdef void calc_and_save_scores(self, out_path, list sent_pairs, bool character_based):
        cdef double entropy = 0
        cdef str src_string, trg_string
        cdef list src_ids, trg_ids
        cdef str record
        cdef int i
        logger.info("calculating and storing alignment scores into file: %s"  % (out_path))
        with files.open(out_path, 'wt') as fobj:
            for i, (src_ids, trg_ids) in enumerate(progress.view(sent_pairs, 'progress')):
                entropy = self.calc_pair_entropy(src_ids, trg_ids, True)
                src_string, trg_string = self.vocab.ids_pair_to_str_pair(src_ids, trg_ids, character_based)
                #record = "%s\t%s\t%s\n" % (entropy, src_string, trg_string)
                record = "{}\n".format(entropy)
                fobj.write(record)

    cdef void decode_and_save_align(self, out_path, list sent_pairs, bool character_based):
        cdef double entropy = 0
        cdef str src_string, trg_string
        cdef list src_ids, trg_ids
        cdef str record
        cdef int i
        cdef ndarray trans_matrix
        logger.info("decoding and storing alignment into file: %s"  % (out_path))
        with files.open(out_path, 'wt') as fobj:
            for i, (src_ids, trg_ids) in enumerate(progress.view(sent_pairs, 'progress')):
                len_src = len(src_ids)
                len_trg = len(trg_ids)
                src_range = list(range(len_src))
                trg_range = list(range(len_trg))
                trans_matrix = sub_matrix(self.trans_dist, src_ids, trg_ids)
                align_matrix = self.align_dist[len_src-2,len_trg-1][:len_trg,:len_src].T
                align_trans_matrix = align_matrix * trans_matrix
                align = []
                #indices = np.where(align_trans_matrix > 0)
                #for index_src, index_trg in zip(*indices):
                #    prob = align_trans_matrix[index_src, index_trg]
                #    if prob > 0.01:
                #        align.append('{}-{}'.format(index_src,index_trg+1))
                for index_trg in range(len_trg):
                    index_src = np.argpartition(-align_trans_matrix[:,index_trg], 1)[0]
                    prob = align_trans_matrix[index_src, index_trg]
                    #dprint([index_src, index_trg, prob])
                    #if prob > 0.01:
                    #    align.append('{}-{}'.format(index_src,index_trg+1))
                    align.append('{}-{}'.format(index_trg+1,index_src))
                record = "{}\n".format(str.join(' ', align))
                fobj.write(record)

    cdef void save_trans_dist(self, out_path, threshold, nbest):
        #cdef tuple indices
        cdef int src, trg
        cdef float prob
        cdef str record
        cdef list src_indices = list(range(len(self.vocab.src)))
        cdef list trg_indices = list(range(len(self.vocab.trg)))
        with files.open(out_path, 'wt') as fobj:
            logger.info("storing translation probabilities into file (threshold=%s): %s" % (threshold,out_path))
            for src in progress.view(src_indices, 'storing'):
                if nbest is not None:
                    nbest = min(nbest, len(self.vocab.trg))
                    trg_indices = list(np.argpartition(-self.trans_dist[src], nbest)[:nbest])
                for trg in trg_indices:
                    prob = self.trans_dist[src,trg]
                    if prob > threshold:
                        record = "%s\t%s\t%s\n" % (self.vocab.src.id2str(src), self.vocab.trg.id2str(trg), prob)
                        fobj.write(record)

    cdef void save_align_dist(self, out_path, threshold):
        cdef tuple indices
        cdef int len_src, len_trg
        cdef int src, trg
        cdef float prob
        cdef str record
        cdef ndarray[float64_t, ndim=3] max_prob = self.align_dist.max(axis=3)
        cdef ndarray[float64_t, ndim=3] min_prob = self.align_dist.min(axis=3)
        cdef ndarray trained = (max_prob != min_prob)
        with files.open(out_path, 'wt') as fobj:
            logger.info("storing alignment probabilities into file: %s" % (out_path,))
            indices = np.where(np.broadcast_to(trained[:,:,:,None], self.align_dist[:].shape))
            for len_src, len_trg, trg, src in progress.view(zip(*indices), 'storing', max_count=len(indices[0])):
                prob = self.align_dist[len_src, len_trg, trg, src]
                if prob > threshold:
                    record = "%s\t%s\t%s\t%s\t%s\n" % (len_src+1, len_trg+1, trg+1, src, prob)
                    fobj.write(record)

cdef class Trainer:
    # imported from "ibm_model1.pxd"
    #cdef Model1 model
    #cdef str src_path
    #cdef str trg_path
    #cdef list sent_pairs
    #cdef np.ndarray cooc_src_trg

    def __init__(self, conf, **others):
        dprint("base trainer __init__")
        self.init()
        conf = Config(conf)
        conf.update(**others)
        if conf.has(['src_path', 'trg_path']):
            self.src_path = conf.data.src_path
            self.trg_path = conf.data.trg_path
        self.character_based = conf.get('character', False)
    cdef void init(self) except *:
        raise NotImplementedError()

    cdef void init_trans_dist(self) except *:
        raise NotImplementedError()

    cdef void init_align_dist(self) except *:
        raise NotImplementedError()

    cdef void expect_step(self) except *:
        raise NotImplementedError()

    cdef void maximize_step(self) except *:
        raise NotImplementedError()

    cdef void setup(self) except *:
        if self.sent_pairs is None:
            logger.info("----")
            logger.info("setting up to train/score IBM Models")
            #logger.debug("self => %r"%self)
            self.sent_pairs = self.model.vocab.load_sent_pairs(self.src_path, self.trg_path, self.character_based)
            logger.info("source vocabulary size: {:,d}".format(len(self.model.vocab.src)))
            logger.info("target vocabulary size: {:,d}".format(len(self.model.vocab.trg)))

    cdef void train(self, int iteration_limit) except *:
        raise NotImplementedError()

    cdef void train_step(self) except *:
        if len(self.model.trans_dist) == 0:
            self.setup()
        else:
            self.expect_step()
            self.maximize_step()

def check_train_config(conf):
    logger.debug("conf => %r"%(conf,))
    #logger.debug(conf)
    #save_trans_path = conf.get('save_trans_path', None)
    #save_align_path = conf.get('save_align_path', None)
    #if not any [save_trans_path, save_align_path]:
    #    logger.error("At least one of arguments is necessary: --save-trans-path/--save_align_path")
    #    return False
    return True

def check_test_config(conf):
    logger.debug("conf => %r"%(conf,))
    save_score_path = conf.get('save_scores', None)
    decode_align_path = conf.get('save_scores', None)
    if not any([save_score_path, decode_align_path]):
        logger.error("At least one of following arguments is necessary:")
        logger.error("* --save-scores | --scores | -s")
        logger.error("* --decode-align | --decode | -d")
        return False
    return True

def train_ibm_models(conf, **others):
    conf = Config(conf)
    conf.update(others)
    if not check_train_config(conf):
        return False
    #trainer = Trainer(conf, **others)
    #trainer = Model1Trainer(conf, **others)
    trainer = Model2Trainer(conf, **others)
    character_based = conf.get('character_based', False)
    try:
        #with np.errstate(all='raise'):
        #    trainer.train(conf.data.iteration_limit)
        Model1Trainer.train(trainer, conf.data.iteration_limit)
        Model2Trainer.train(trainer, conf.data.iteration_limit)
    except KeyboardInterrupt as k:
        logger.warning('interuppted by keyboard')
        logger.info("forcing to dump alignments and scores")
    except Exception as e:
        logger.exception(e)
    logger.info("----")
    trainer.model.save_trans_dist(conf.data.save_trans_path, conf.data.threshold, conf.data.nbest)
    if conf.data.save_align_path:
        trainer.model.save_align_dist(conf.data.save_align_path, conf.data.threshold)
    if conf.data.save_scores:
        trainer.model.calc_and_save_scores(conf.data.save_scores, trainer.sent_pairs, character_based)
    if conf.data.decode_align:
        trainer.model.decode_and_save_align(conf.data.decode_align, trainer.sent_pairs, character_based)
    logger.info("----")
    return True

def score_ibm_model(conf, **others):
    conf = Config(conf)
    conf.update(others)
    if not check_test_config(conf):
        return False
    #trainer = Trainer(conf, **others)
    trainer = Model2Trainer(conf, **others)
    character_based = conf.get('character', False)
    try:
        sent_pairs = trainer.model.vocab.load_sent_pairs(conf.data.src_path, conf.data.trg_path, character_based)
        dprint(sent_pairs)
        with open(conf.data.trans_path) as fobj:
            for line in fobj:
                fields = line.strip().split('\t')
                if len(fields) == 3:
                    src, trg, prob = fields
                    trainer.model.vocab.src.str2id(src)
                    trainer.model.vocab.trg.str2id(trg)
        #trainer.model.trans_dist = trainer.init_trans_dist()
        trainer.setup()
        logger.info("loading word translation distribution file: {}".format(conf.data.trans_path))
        with progress.view(conf.data.trans_path) as fobj:
            for line in fobj:
                fields = line.strip().split('\t')
                if len(fields) == 3:
                    src, trg, prob = fields
                    src = trainer.model.vocab.src.str2id(src)
                    trg = trainer.model.vocab.trg.str2id(trg)
                    prob = float(prob)
                    trainer.model.trans_dist[src,trg] = prob
        if conf.data.align_path is not None:
            logger.info("loading alignment distribution file: {}".format(conf.data.align_path))
            with progress.view(conf.data.align_path) as fobj:
                for line in fobj:
                    fields = line.strip().split('\t')
                    if len(fields) == 5:
                        len_src, len_trg, pos_trg, pos_src = [int(index) for index in fields[0:4]]
                        prob = float(fields[4])
                        trainer.model.align_dist[len_src-1,len_trg-1,pos_trg-1,pos_src] = prob
        if conf.data.save_scores:
            trainer.model.calc_and_save_scores(conf.data.save_scores, sent_pairs, character_based)
        if conf.data.decode_align:
            trainer.model.decode_and_save_align(conf.data.decode_align, sent_pairs, character_based)
    except KeyboardInterrupt as k:
        logger.exception(k)
    except Exception as e:
        logger.exception(e)
    return True

def create_train_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('src_path', metavar='src_path (in)', help='file containing source-side lines of parallel text', type=str)
    parser.add_argument('trg_path', help='file containing target-side lines of parallel text', type=str)
    parser.add_argument('save_trans_path', help='output file to save translation probabilities', type=str)
    parser.add_argument('save_align_path', help='output file to save alignment probabilities', type=str, nargs='?')
    #parser.add_argument('save_align_path', help='output file to save alignment probabilities', type=str, nargs='?', default=None)
    #parser.add_argument('--save-trans-path', help='output file to save translation distribution', type=str)
    #parser.add_argument('--save-align-path', help='output file to save alignment probabilities', type=str)
    parser.add_argument('--save-scores', '--scores', '-s', help='output file to save entropy of each alignment', type=str, default=None)
    parser.add_argument('--decode-align', '--decode', '-d', help='output file to save decoded alignment each alignment', type=str, default=None)
    parser.add_argument('--iteration-limit', '-I', help='maximum iteration number of EM algorithm (default: %(default)s)', type=int, default=ITERATION_LIMIT)
    parser.add_argument('--threshold', '-t', help='threshold of translation distribution to save', type=float, default=THRESHOLD)
    parser.add_argument('--nbest', '-n', help='limit number of records to save, taking top-n of "p(trg|src)"', type=int, default=NBEST)
    parser.add_argument('--character', '-c', help='chacacter based alignment mode', action='store_true')
    parser.add_argument('--debug', '-D', help='debug mode', action='store_true')
    parser.add_argument('--quiet', '-q', help='not showing staging log', action='store_true')
    return parser

def create_score_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('src_path', metavar='src_path (in)', help='file containing source-side lines of parallel text', type=str)
    parser.add_argument('trg_path', help='file containing target-side lines of parallel text', type=str)
    parser.add_argument('trans_path', help='path to load trained translation probabilities', type=str)
    parser.add_argument('align_path', help='path to load trained alignment probabilities', type=str, nargs='?')
    #parser.add_argument('score_path', help='output file to save entropy of each each alignment', type=str)
    parser.add_argument('--save-scores', '--scores', '-s', help='output file to save entropy of each alignment', type=str, default=None)
    parser.add_argument('--decode-align', '--decode', '-d', help='output file to save decoded alignment each alignment', type=str, default=None)
    parser.add_argument('--character', '-c', help='chacacter based alignment mode', action='store_true')
    parser.add_argument('--debug', '-D', help='debug mode', action='store_true')
    parser.add_argument('--quiet', '-q', help='not showing staging log', action='store_true')
    return parser

def train_model(parser, train_func):
    args = parser.parse_args()
    conf = Config(vars(args))
    #with logging.using_config(logger) as c:
    with logging.using_config(['lpu', '__main__']) as c:
        if conf.data.debug:
            c.set_debug(True)
            c.set_quiet(False)
        if conf.data.quiet:
            c.set_quiet(True)
            c.set_debug(False)
        dprint(args)
        dprint(conf)
        train_func(conf)

def score_model(parser, score_func):
    args = parser.parse_args()
    conf = Config(vars(args))
    #with logging.using_config(logger) as c:
    with logging.using_config(['lpu', '__main__']) as c:
        if conf.data.debug:
            c.set_debug(True)
            c.set_quiet(False)
        if conf.data.quiet:
            c.set_quiet(True)
            c.set_debug(False)
        logger.debug(conf)
        score_func(conf)

def main_train():
    return train_model(create_train_parser(), train_ibm_models)

def main_score():
    return score_model(create_score_parser(), score_ibm_model)

if __name__ == '__main__':
    main_train()

