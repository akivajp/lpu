# distutils: language=c++
# -*- coding: utf-8 -*-

# C++ set-up
from libcpp cimport bool

# 3-rd party library
import numpy as np
cimport numpy as np
from numpy cimport ndarray
from numpy cimport float64_t

# Local libraries

from lpu.common import progress
from lpu.common import logging

from . ibm_models cimport sub_matrix
from . ibm_models cimport grid_indices
from . ibm_models cimport normalize

logger = logging.getColorLogger(__name__)
dprint = logger.debug_print

cdef class Model1:
    cdef double calc_pair_entropy(self, list src_sent, list trg_sent, bool normalize) except *:
        cdef np.ndarray trans_matrix
        trans_matrix = sub_matrix(self.trans_dist, src_sent, trg_sent)
        if normalize:
            return (-np.log(trans_matrix.sum(axis=0) / len(src_sent)).sum()) / len(trg_sent)
        else:
            return -np.log(trans_matrix.sum(axis=0) / len(src_sent)).sum()

cdef class Model1Trainer:
    cdef void init(self) except *:
        dprint("trainer 1 init")
        self.model = Model1()
        dprint(self.model)

    cdef void init_trans_dist(self) except *:
        cdef int len_src = len(self.model.vocab.src)
        cdef int len_trg = len(self.model.vocab.trg)
        #cdef np.ndarray uniform_dist
        cdef ndarray[float64_t, ndim=2] uniform_dist
        logger.info("initializing word translation probabilities as uniform distribution")
        uniform_dist = np.ones([len_src, len_trg], np.float64) / len_trg
        msg = "word translation distribution matrix size: {} [src words] x {} [trg words] x {} [bytes] = {:,d} [bytes]"
        #logger.info(msg.format(len_src,len_trg,uniform_dist.itemsize,len(uniform_dist.data)))
        logger.info(msg.format(len_src,len_trg,uniform_dist.itemsize,uniform_dist.nbytes))
        #return uniform_dist
        self.model.trans_dist = uniform_dist

    cdef void expect_step(self) except *:
        cdef int len_src = len(self.model.vocab.src)
        cdef int len_trg = len(self.model.vocab.trg)
        cdef list src_sent, trg_sent
        cdef tuple cooc
        cdef np.ndarray cooc_trans_dist
        self.count_cooc_src2trg = np.zeros([len_src, len_trg], np.float64)
        logger.info('computing expected co-occurrence counts of source word and target word')
        for i, (src_sent, trg_sent) in enumerate(progress.view(self.sent_pairs, 'processing')):
            cooc = grid_indices(src_sent, trg_sent)
            cooc_trans_dist = sub_matrix(self.model.trans_dist, src_sent, trg_sent)
            ## normalizing factor
            normalize(cooc_trans_dist, 0, cooc_trans_dist)
            np.add.at(self.count_cooc_src2trg, cooc, cooc_trans_dist)

    cdef void maximize_step(self) except *:
        cdef ndarray[float64_t, ndim=2] total_src
        logger.info("estimating word translation distribution")
        #total_src = self.count_cooc_src2trg.sum(axis=1).reshape(-1,1)
        #self.model.trans_dist = self.count_cooc_src2trg / total_src
        normalize(self.count_cooc_src2trg, 1, self.model.trans_dist)

    cdef void setup(self) except *:
        #super(Model1Trainer,self).train_setup()
        #logger.debug("self => %r"%self)
        Trainer.setup(self)
        if self.model.trans_dist is None:
            self.init_trans_dist()

    cdef void train(self, int iteration_limit) except *:
        cdef double last_entropy
        self.setup()
        logger.info("----")
        logger.info("start training IBM Model 1")
        last_entropy = self.model.calc_entropy(self.sent_pairs)
        logger.info("initial entropy: %s" % last_entropy)
        for step in range(iteration_limit):
            logger.info("--")
            logger.info("step: {} / {}".format(step+1, iteration_limit))
            # train 1 step
            Model1Trainer.train_step(self)
            # calculate entropy
            entropy = self.model.calc_entropy(self.sent_pairs)
            logger.info("entropy: %s" % entropy)
            if entropy >= last_entropy:
                break
            else:
                last_entropy = entropy

    cdef void train_step(self) except *:
        if self.model.trans_dist is None:
            self.setup()
        else:
            Model1Trainer.expect_step(self)
            Model1Trainer.maximize_step(self)

