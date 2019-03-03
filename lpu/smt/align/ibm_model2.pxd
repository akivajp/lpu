# 3-rd party library
cimport numpy as np
from numpy cimport ndarray

# local
from ibm_model1 cimport Model1
from ibm_model1 cimport Model1Trainer

cdef class Model2(Model1):
    pass

cdef class Model2Trainer(Model1Trainer):
    pass

