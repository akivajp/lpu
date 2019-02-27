# distutils: language=c++
# -*- coding: utf-8 -*-

# Standard libraries
import argparse

# 3-rd party library
import numpy as np
cimport numpy as np

# Local libraries

from lpu.common import environ
from lpu.common import files
from lpu.common import progress
from lpu.common import logging

#from lpu.common.config import Config
from lpu.common.config cimport Config
from lpu.common.vocab cimport StringEnumerator
from lpu.common import logging

logger = logging.getColorLogger(__name__)
dprint = logger.debug_print

#logger = logging.getLogger(__name__)

ITERATION_LIMIT = 10

NULL_SYMBOL = '__NULL__'

cdef class Vocab:
    # imported from "ibm_model1.pxd"
    #cdef StringEnumerator src
    #cdef StringEnumerator trg

    def __cinit__(self):
        self.init()
    cdef void init(self):
        self.src = StringEnumerator()
        self.trg = StringEnumerator()

    cpdef tuple ids_pair_to_str_pair(self, src_ids, trg_ids):
        cdef src_str = str.join(' ', [self.src.id2str(i) for i in src_ids[:-1]])
        cdef trg_str = str.join(' ', [self.trg.id2str(i) for i in trg_ids])
        return src_str, trg_str

    cpdef list load_sent_pairs(self, str src_path, str trg_path):
        cdef str src_line, trg_line
        cdef list src_words, trg_words
        cdef list src_ids, trg_ids
        cdef list sent_pairs
        cdef str word
        logger.info("loading files: %s %s" % (src_path,trg_path))
        self.src.append(NULL_SYMBOL)
        #src_file = progress.view(files.open(src_path), 'loading')
        #src_file = progress.view(files.open(src_path), 'loading').read_byte_lines()
        #src_file = progress.view(src_path, 'loading').read_byte_lines()
        src_file = progress.FileReader(src_path, 'loading')
        #src_file = progress.FileReader(src_path, 'loading').read_byte_lines()
        trg_file = files.open(trg_path)
        #trg_file = files.open(trg_path, 'rb')
        sent_pairs = []
        for src_line, trg_line in zip(src_file, trg_file):
            src_words = src_line.rstrip("\n").split(' ')
            trg_words = trg_line.rstrip("\n").split(' ')
            #src_words = src_line.rstrip(b"\n").split(b' ')
            #trg_words = trg_line.rstrip(b"\n").split(b' ')
            src_words.append(NULL_SYMBOL)
            src_ids = [self.src.str2id(word) for word in src_words]
            trg_ids = [self.trg.str2id(word) for word in trg_words]
            sent_pairs.append( (src_ids, trg_ids) )
        return sent_pairs

cdef tuple grid_indices(list x_indices, list y_indices):
    cdef np.ndarray indices1, indices2
    indices1, indices2 = np.meshgrid(x_indices, y_indices, sparse=True)
    return indices1.T, indices2.T

cdef np.ndarray sub_matrix(np.ndarray matrix, list x_indices, list y_indices):
    return matrix[grid_indices(x_indices, y_indices)]

#cdef void add_sub_matrix(np.ndarray target_matrix, list x_indices, list y_indices, np.ndarray source_matrix):
#    cdef np.ndarray indices1, indices2
#    indices1, indices2 = grid_indices(x_indices, y_indices)
#    np.add.at(target_matrix, (indices1,indices2), source_matrix[indices1,indices2])

cdef class Model:
    # imported from "ibm_model1.pxd"
    #cdef np.ndarray trans_dist
    #cdef Vocab vocab

    def __cinit__(self):
        self.init()
    cdef inline void init(self):
        self.vocab = Vocab()

    #cpdef double calc_pair_entropy(self, list src_sent, list trg_sent):
    cpdef double calc_pair_entropy(self, list src_sent, list trg_sent) except *:
        cdef np.ndarray trans_matrix
        trans_matrix = sub_matrix(self.trans_dist, src_sent, trg_sent)
        #return -np.log(trans_matrix.sum(axis=0) / len(src_sent)).sum()
        return (-np.log(trans_matrix.sum(axis=0) / len(src_sent)).sum()) / len(trg_sent)

    cpdef double calc_entropy(self, list sent_pairs) except *:
        cdef float total_entropy = 0
        logger.info('calculating entropy')
        for i, (src_sent, trg_sent) in enumerate(progress.view(sent_pairs, 'progress')):
            total_entropy += self.calc_pair_entropy(src_sent, trg_sent)
        return total_entropy / len(sent_pairs)

    cpdef void calc_and_save_scores(self, out_path, list sent_pairs):
        cdef double entropy = 0
        cdef str src_string, trg_string
        cdef list src_ids, trg_ids
        cdef str record
        logger.info("calculating and storing into file: %s"  % (out_path))
        with files.open(out_path, 'wt') as fobj:
            for i, (src_ids, trg_ids) in enumerate(progress.view(sent_pairs, 'progress')):
                entropy = self.calc_pair_entropy(src_ids, trg_ids)
                src_string, trg_string = self.vocab.ids_pair_to_str_pair(src_ids, trg_ids)
                record = "%s\t%s\t%s\n" % (entropy, src_string, trg_string)
                fobj.write(record)

    cpdef void save_align(self, out_path, threshold):
        cdef tuple indices
        cdef int src, trg
        cdef float prob
        cdef str record
        with files.open(out_path, 'wt') as fobj:
            logger.info("storing translation probabilities into file (threshold=%s): %s" % (threshold,out_path))
            indices = np.where(self.trans_dist>= threshold)
            for src, trg in progress.view(zip(*indices), 'storing', max_count=len(indices[0])):
                prob = self.trans_dist[src,trg]
                record = "%s\t%s\t%s\n" % (self.vocab.src.id2str(src), self.vocab.trg.id2str(trg), prob)
                fobj.write(record)

cdef class Trainer:
    # imported from "ibm_model1.pxd"
    #cdef Model model
    #cdef str src_path
    #cdef str trg_path
    #cdef list sent_pairs
    #cdef np.ndarray cooc_src_trg

    def __cinit__(self, conf, **others):
        self.init()
        conf = Config(conf)
        conf.update(**others)
        if conf.has(['src_path', 'trg_path']):
            self.src_path = conf.data.src_path
            self.trg_path = conf.data.trg_path
    cdef void init(self):
        self.model = Model()

    cpdef np.ndarray calc_uniform_dist(self):
        cdef StringEnumerator vocab_src = self.model.vocab.src
        cdef StringEnumerator vocab_trg = self.model.vocab.trg
        cdef np.ndarray uniform_dist
        cdef int src, trg
        logger.info("calculating uniform distribution for word translation probability")
        uniform_dist = np.ones([len(vocab_src), len(vocab_trg)], np.float64) / len(vocab_trg)
        logger.info("word trans. distribution matrix size: %s [src words] x %s [trg words] x %s [bytes] = %s [bytes]"
            % (uniform_dist.shape[0],uniform_dist.shape[1],uniform_dist.itemsize,len(uniform_dist.data)))
        return uniform_dist

    cpdef np.ndarray count_cooccurrence(self, sent_pairs):
        cdef StringEnumerator vocab_src = self.model.vocab.src
        cdef StringEnumerator vocab_trg = self.model.vocab.trg
        cdef np.ndarray cooc_src_trg
        cdef int src, trg
        cdef np.ndarray src_indices, trg_indices
        cooc_src_trg = np.zeros([len(vocab_src),len(vocab_trg)], np.int)
        logger.info('counting co-occurrences of source word and target word')
        for i, (src_sent, trg_sent) in enumerate(progress.view(sent_pairs, 'processing')):
            #np.add.at(cooc_src_trg, np.meshgrid(src_sent,trg_sent), 1)
            np.add.at(cooc_src_trg, grid_indices(src_sent, trg_sent), 1)
        logger.info("co-occurrence matrix size: %s [src words] x %s [trg words] x %s [bytes]= %s [bytes]"
            % (cooc_src_trg.shape[0],cooc_src_trg.shape[1],cooc_src_trg.itemsize,cooc_src_trg.size*cooc_src_trg.itemsize))
        return cooc_src_trg

    cpdef void train(self, int iteration_limit):
    #cpdef void train(self, int iteration_limit) except *:
        cdef double last_entropy
        logger.info("start training IBM Model 1")
        self.train_first()
        last_entropy = self.model.calc_entropy(self.sent_pairs)
        logger.info("initial entropy: %s" % last_entropy)
        for step in range(iteration_limit):
            logger.info("--")
            logger.info("step: %s" % (step + 1))
            # train 1 step
            self.train_step()
            # calculate entropy
            entropy = self.model.calc_entropy(self.sent_pairs)
            logger.info("entropy: %s" % entropy)
            if entropy == last_entropy:
                break
            else:
                last_entropy = entropy

    cpdef void train_first(self):
        self.sent_pairs = self.model.vocab.load_sent_pairs(self.src_path, self.trg_path)
        logger.info("source vocabulary size: {:,d}".format(len(self.model.vocab.src)))
        logger.info("target vocabulary size: {:,d}".format(len(self.model.vocab.trg)))
        self.cooc_src_trg = self.count_cooccurrence(self.sent_pairs)
        self.model.trans_dist = self.calc_uniform_dist()

    cpdef void train_step(self):
        cdef long i
        cdef list src_sent, trg_sent
        cdef np.ndarray count_src2trg, total_src
        cdef np.ndarray trg_factor
        cdef StringEnumerator vocab_src = self.model.vocab.src
        cdef StringEnumerator vocab_trg = self.model.vocab.trg
        cdef tuple grid

        if len(self.model.trans_dist) == 0:
            self.train_first()
        else:
            count_src2trg = np.zeros([len(vocab_src),len(vocab_trg),], np.float64)
            total_src = np.zeros(len(vocab_src), np.float64)
            logger.info("estimating expected co-occurrence counts")
            for i, (src_sent, trg_sent) in enumerate(progress.view(self.sent_pairs, 'processing')):
                grid = grid_indices(src_sent, trg_sent)
                # compute normalization
                trg_factor = np.zeros(len(vocab_trg), np.float64)
                np.add.at(trg_factor, trg_sent, sub_matrix(self.model.trans_dist,src_sent,trg_sent).sum(axis=0))
                # collect counts
                np.add.at(count_src2trg, grid,     self.model.trans_dist[grid] / trg_factor[trg_sent])
                np.add.at(total_src, src_sent, (self.model.trans_dist[grid] / trg_factor[trg_sent]).sum(axis=1))
            # estimate probabilities
            logger.info("estimating word translation probabilities")
            self.model.trans_dist = count_src2trg / total_src.reshape([-1,1])

def check_config(conf):
    logger.debug(conf)

def train_ibm_model1(conf, **others):
    with environ.push() as e:
        conf = Config(conf)
        conf.update(others)
        check_config(conf)
        trainer = Trainer(conf, **others)
        try:
            #np.seterr(all='raise')
            #trainer.train(conf.data.iteration_limit)
            with np.errstate(all='raise'):
                trainer.train(conf.data.iteration_limit)
        except KeyboardInterrupt as k:
            logger.debug(k)
            logger.info("forcing to dump alignments and scores")
        #except Exception as e:
        #    logger.debug(e)
        #    logger.info("forcing to dump alignments and scores")
        trainer.model.save_align(conf.data.save_align_path, conf.data.threshold)
        if conf.data.save_scores:
            trainer.model.calc_and_save_scores(conf.data.save_scores, trainer.sent_pairs)

def score_ibm_model1(conf, **others):
    with environ.push() as e:
        conf = Config(conf)
        conf.update(others)
        check_config(conf)
        trainer = Trainer(conf, **others)
        #model = Model()
        try:
            sent_pairs = trainer.model.vocab.load_sent_pairs(conf.data.src_path, conf.data.trg_path)
            with open(conf.data.align_path) as fobj:
                for line in fobj:
                    fields = line.strip().split('\t')
                    #if len(fields) == 3:
                    src, trg, prob = fields
                    trainer.model.vocab.src.str2id(src)
                    trainer.model.vocab.trg.str2id(src)
            trainer.model.trans_dist = trainer.calc_uniform_dist()
            logger.info("loading word alignment file")
            with open(conf.data.align_path) as fobj:
                for line in fobj:
                    fields = line.strip().split('\t')
                    #if len(fields) == 3:
                    src, trg, prob = fields
                    src = trainer.model.vocab.src.str2id(src)
                    trg = trainer.model.vocab.src.str2id(trg)
                    prob = float(prob)
                    #dprint(src)
                    #dprint(trg)
                    #dprint(trainer.model.trans_dist[src,trg],)
                    trainer.model.trans_dist[src,trg] = prob
                    #dprint(trainer.model.trans_dist[src,trg],)
            trainer.model.trans_dist /= len(trainer.model.vocab.trg)
            #logger.info("calculating and saving the alignment scores")
            trainer.model.calc_and_save_scores(conf.data.score_path, sent_pairs)
            #with np.errstate(all='raise'):
            #    trainer.train(conf.data.iteration_limit)
        except KeyboardInterrupt as k:
            logger.exception(k)

def main_train():
    parser = argparse.ArgumentParser()
    parser.add_argument('src_path', metavar='src_path (in)', help='file containing source-side lines of parallel text', type=str)
    parser.add_argument('trg_path', help='file containing target-side lines of parallel text', type=str)
    parser.add_argument('save_align_path', help='output file to save alignment', type=str)
    parser.add_argument('--save-scores', '-S', help='output file to save entropy of each each alignment', type=str, default=None)
    parser.add_argument('--iteration-limit', '-I', help='maximum iteration number of EM algorithm (default: %(default)s)', type=int, default=ITERATION_LIMIT)
    parser.add_argument('--threshold', '-t', help='threshold of translation probabilities to save', type=float, default=0.01)
    #parser.add_argument('--character', '-c', help='chacacter based alignment mode', action='store_true')
    parser.add_argument('--debug', '-D', help='debug mode', action='store_true')
    parser.add_argument('--quiet', '-q', help='not showing staging log', action='store_true')
    args = parser.parse_args()
    conf = Config(vars(args))
    with logging.using_config(logger) as c:
        if conf.data.debug:
            c.set_debug(True)
            c.set_quiet(False)
        if conf.data.quiet:
            c.set_quiet(True)
            c.set_debug(False)
        logger.debug(conf)
        train_ibm_model1(conf)

def main_score():
    parser = argparse.ArgumentParser()
    parser.add_argument('src_path', metavar='src_path (in)', help='file containing source-side lines of parallel text', type=str)
    parser.add_argument('trg_path', help='file containing target-side lines of parallel text', type=str)
    parser.add_argument('align_path', help='path to trained alignment', type=str)
    parser.add_argument('score_path', help='output file to save entropy of each each alignment', type=str)
    parser.add_argument('--debug', '-D', help='debug mode', action='store_true')
    parser.add_argument('--quiet', '-q', help='not showing staging log', action='store_true')
    args = parser.parse_args()
    conf = Config(vars(args))
    with logging.using_config(logger) as c:
        if conf.data.debug:
            c.set_debug(True)
            c.set_quiet(False)
        if conf.data.quiet:
            c.set_quiet(True)
            c.set_debug(False)
        logger.debug(conf)
        score_ibm_model1(conf)

if __name__ == '__main__':
    main_train()

