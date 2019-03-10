# C++ set-up
from libcpp cimport bool

# 3-rd party library
cimport numpy as np
from numpy cimport ndarray
from numpy cimport float64_t

# local library
from lpu.common.vocab cimport StringEnumerator

cdef class Vocab:
    cdef StringEnumerator src
    cdef StringEnumerator trg
    cdef int max_len_src
    cdef int max_len_trg

    cdef void init(self)
    cdef tuple ids_pair_to_str_pair(self, src_ids, trg_ids, bool character_based)
    cdef list load_sent_pairs(self, str src_path, str trg_path, bool character_based)

cdef class Model:
    cdef Vocab vocab
    cdef np.ndarray trans_dist
    cdef np.ndarray align_dist

    cdef void init(self)
    cdef double calc_pair_entropy(self, list src_sent, list trg_sent, bool normalize) except *
    cdef double calc_entropy(self, list sent_pairs) except *
    cdef void calc_and_save_scores(self, out_path, list sent_pairs, bool character_based)
    cdef void decode_and_save_align(self, out_path, list sent_pairs, bool character_based)
    cdef void save_align_dist(self, out_path, threshold)
    cdef void save_trans_dist(self, out_path, threshold, nbest)

cdef class Trainer:
    cdef Model model
    cdef str src_path
    cdef str trg_path
    cdef list sent_pairs
    cdef bool character_based
    cdef np.ndarray count_cooc_src2trg
    cdef np.ndarray count_align_trg2src

    cdef void init(self) except *

    cdef void init_trans_dist(self) except *
    cdef void init_align_dist(self) except *
    cdef void expect_step(self) except *
    cdef void maximize_step(self) except *
    cdef void save_align_dist(self, out_path, threshold) except *
    cdef void save_trans_dist(self, out_path, threshold, nbest) except *
    cdef void setup(self) except *
    cdef void train(self, int iteration_limit) except *
    cdef void train_step(self) except *

cdef tuple grid_indices(list x_indices, list y_indices)
cdef ndarray[float64_t,ndim=2] sub_matrix(ndarray[float64_t,ndim=2] matrix, list x_indices, list y_indices)
cdef ndarray normalize(ndarray tensor, int axis, ndarray target)

