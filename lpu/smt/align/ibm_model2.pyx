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
from . ibm_model1 cimport Model1Trainer

logger = logging.getColorLogger(__name__)
dprint = logger.debug_print

cdef class Model2:
    cdef double calc_pair_entropy(self, list src_sent, list trg_sent, bool normalize) except *:
        cdef int len_src = len(src_sent)
        cdef int len_trg = len(trg_sent)
        cdef list src_range = list(range(len_src))
        cdef list trg_range = list(range(len_trg))
        cdef np.ndarray trans_matrix, align_matrix, align_trans_matrix
        trans_matrix = sub_matrix(self.trans_dist, src_sent, trg_sent)
        align_matrix = self.align_dist[len_src-2, len_trg-1][:len_trg,:len_src].T
        align_trans_matrix = align_matrix * trans_matrix
        if normalize:
            return -np.log(align_trans_matrix.sum(axis=0)).sum() / len(trg_sent)
        else:
            return -np.log(align_trans_matrix.sum(axis=0)).sum()

cdef class Model2Trainer:
    cdef void init(self) except *:
        dprint("model 2")
        self.model = Model2()

    cdef void init_align_dist(self) except *:
        #cdef np.ndarray uniform_dist
        cdef ndarray[float64_t, ndim=4] uniform_dist
        cdef int max_len_src = self.model.vocab.max_len_src
        cdef int max_len_trg = self.model.vocab.max_len_trg
        logger.info("initializing index alignment probabilities as uniform distribution")
        #uniform_dist = np.zeros([max_len_src-1, max_len_trg, max_len_src, max_len_trg], np.float64)
        uniform_dist = np.zeros([max_len_src-1, max_len_trg, max_len_trg, max_len_src], np.float64)
        indices = list( np.ndindex(max_len_src-1, max_len_trg) )
        for index_src, index_trg in progress.view(indices, header='initializing'):
            len_src = index_src + 2
            len_trg = index_trg + 1
            uniform_dist[index_src,index_trg] = 1.0 / float(len_src)
        msg = "word alignment distribution matrix size: {} [src len] x {} [trg len] x {} [trg index] x {} [src index] x {} [bytes] = {:,d} [bytes]"
        logger.info(msg.format(max_len_src-2,max_len_trg-1,max_len_trg,max_len_src,uniform_dist.itemsize,uniform_dist.nbytes))
        self.model.align_dist = uniform_dist

    cdef void expect_step(self) except *:
        cdef int vocab_size_src = len(self.model.vocab.src)
        cdef int vocab_size_trg = len(self.model.vocab.trg)
        cdef int max_len_src = self.model.vocab.max_len_src
        cdef int max_len_trg = self.model.vocab.max_len_trg
        cdef int len_src, len_trg
        cdef list src_sent, trg_sent
        cdef list src_range, trg_range
        cdef tuple cooc, align
        cdef ndarray[float64_t,ndim=2] cooc_trans_dist
        cdef ndarray[float64_t,ndim=2] sent_align_dist
        cdef ndarray[float64_t,ndim=2] align_trans_dist, sum_trg
        self.count_cooc_src2trg  = self.model.trans_dist * 0
        self.count_align_trg2src = self.model.align_dist * 0
        logger.info('computing:')
        logger.info('* expected co-occurrence counts of source word and target word')
        logger.info('* expected alignment counts of source index and target index')
        for i, (src_sent, trg_sent) in enumerate(progress.view(self.sent_pairs, 'processing')):
            len_src = len(src_sent)
            len_trg = len(trg_sent)
            src_range = list(range(len_src))
            trg_range = list(range(len_trg))
            cooc = grid_indices(src_sent, trg_sent)
            align = grid_indices(trg_range, src_range)
            cooc_trans_dist = sub_matrix(self.model.trans_dist, src_sent, trg_sent)
            sent_align_dist = self.model.align_dist[len_src-2,len_trg-1][:len_trg,:len_src].T
            align_trans_dist = cooc_trans_dist * sent_align_dist
            # normalizing factor
            sum_trg = align_trans_dist.sum(axis=0)[None,:]
            align_trans_dist = align_trans_dist / sum_trg
            np.add.at(self.count_cooc_src2trg, cooc, align_trans_dist)
            np.add.at(self.count_align_trg2src[len_src-2,len_trg-1], align, align_trans_dist.T)

    cdef void maximize_step(self) except *:
        logger.info("estimating word translation distribution")
        normalize(self.count_cooc_src2trg,  1, self.model.trans_dist)
        normalize(self.count_align_trg2src, 3, self.model.align_dist)

    cdef void setup(self) except *:
        #logger.debug("self => %r"%self)
        Model1Trainer.setup(self)
        if self.model.align_dist is None:
            self.init_align_dist()

    cdef void train(self, int iteration_limit) except *:
        cdef double last_entropy
        self.setup()
        logger.info("----")
        logger.info("start training IBM Model 2")
        last_entropy = self.model.calc_entropy(self.sent_pairs)
        logger.info("initial entropy: %s" % last_entropy)
        for step in range(iteration_limit):
            logger.info("--")
            logger.info("step: {} / {}".format(step+1, iteration_limit))
            # train 1 step
            Model2Trainer.train_step(self)
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
            Model2Trainer.expect_step(self)
            Model2Trainer.maximize_step(self)

