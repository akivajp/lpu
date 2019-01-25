# 3-rd party library
cimport numpy as np

# local library
from lpu.common.vocab cimport StringEnumerator

cdef class Vocab:
    cdef StringEnumerator src
    cdef StringEnumerator trg

    cdef void init(self)
    cpdef tuple ids_pair_to_str_pair(self, src_ids, trg_ids)
    cpdef list load_sent_pairs(self, str src_path, str trg_path)

cdef class Model:
    cdef Vocab vocab
    cdef np.ndarray trans_dist

    cdef void init(self)
    #cpdef double calc_pair_entropy(self, list src_sent, list trg_sent)
    cpdef double calc_pair_entropy(self, list src_sent, list trg_sent) except *
    cpdef double calc_entropy(self, list sent_pairs) except *
    cpdef void calc_and_save_scores(self, out_path, list sent_pairs)
    cpdef void save_align(self, out_path, threshold)

cdef class Trainer:
    cdef Model model
    cdef str src_path
    cdef str trg_path
    cdef list sent_pairs
    cdef np.ndarray cooc_src_trg

    cdef void init(self)
    #cpdef void init(self)
    #cdef inline void init(self):
    #    self.model = Model()

    cpdef np.ndarray calc_uniform_dist(self)
    cpdef np.ndarray count_cooccurrence(self, sent_pairs)
    cpdef void train(self, int iteration_limit)
    #cpdef void train(self, int iteration_limit) except *
    cpdef void train_first(self)
    cpdef void train_step(self)

