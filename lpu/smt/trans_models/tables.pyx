# distutils: language=c++
# -*- coding: utf-8 -*-

'''classes handling phrase/rule table'''

from libcpp cimport bool

# 3rd party library
import pycedar

# Local libraries
from lpu.common import logging
from lpu.common import progress
from lpu.smt.trans_models import records

key_types = ['src', 'src_hiero', 'src_symbols', 'src_tree']

#cdef get_track_str(object trie, str key):
#    return str(trie.get_node(key)).replace(' ', '')
    #return str(node.track()).replace(' ', '')
cdef get_track_str(object node):
    return str(node.track()).replace(' ', '')

cdef track2key(object trie_dict, str track):
    cdef list numbers
    cdef size_t node_id, length
    numbers = track[1:-1].split(',')
    node_id = int(numbers[0])
    length  = int(numbers[1])
    return trie_dict.trie.suffix(node_id, length)

cdef class Table(object):
    cdef readonly object RecordClass
    cdef str table_path
    cdef object table_file
    cdef str key_type
    cdef readonly object field_dict
    #cdef object record_dict
    cdef readonly object record_dict
    #cdef readonly object trg_record_dict
    #cdef readonly object key_record_dict
    cdef readonly object src_record_dict
    cdef readonly object trg_record_dict
    cdef readonly object trg_field_record_dicts
    cdef bool trg_key_enabled

    def __init__(self, table_path, RecordClass, trg_key = False, **options):
        self.key_type = options.get('key_type', 'src')
        self.RecordClass = RecordClass
        self.table_path = table_path
        self.field_dict  = pycedar.dict(str)
        self.record_dict = pycedar.dict(str)
        #self.key_record_dict    = pycedar.dict(str)
        self.src_record_dict    = pycedar.dict(str)
        #if trg_key:
        #    self.trg_record_dict = pycedar.dict(str)
        #else:
        #    self.trg_record_dict = None
        self.trg_key_enabled = trg_key
        if trg_key:
            self.trg_record_dict = pycedar.dict(str)
            self.trg_field_record_dicts = []
        self.__load()

    #cdef add_key_and_node(self, str key, object record_node):
    #    cdef str key_track, pair_tracks
    #    key_track = get_track_str(self.field_dict.get_node(key))
    #    pair_tracks = "%s | %s" % (key_track, get_track_str(record_node))
    #    self.key_record_dict.update(pair_tracks, 1)

    cdef add_key_and_node(self, object key_record_dict, str key, object record_node):
        cdef str key_track, pair_tracks
        key_track = get_track_str(self.field_dict.get_node(key))
        pair_tracks = "%s | %s" % (key_track, get_track_str(record_node))
        #self.key_record_dict.update(pair_tracks, 1)
        key_record_dict.update(pair_tracks, 1)

    cdef add_fields(self, str line):
        cdef str field
        for field in line.split('|||'):
            field = field.strip()
            if field:
                try:
                    self.field_dict.update(field, 1)
                except Exception as e:
                    logging.debug(e)
                    logging.debug(field)

    cpdef str format_src_key(self, str src):
        if self.key_type == 'src':
            #return src + ' ||| '
            return src
        elif self.key_type == 'src_hiero':
            #return str.join(' ', self.RecordClass.getSymbols(src,hiero=True)) + ' ||| '
            return str.join(' ', self.RecordClass.getSymbols(src,hiero=True))
        elif self.key_type == 'src_symbols':
            #return str.join(' ', self.RecordClass.getSymbols(src,hiero=False)) + ' ||| '
            return str.join(' ', self.RecordClass.getSymbols(src,hiero=False))

    cpdef str line2tracks(self, str line):
        cdef list track_list = []
        cdef str str_track
        for field in line.split('|||'):
            field = field.strip()
            if len(field) == 0:
                track_list.append('')
            elif field in self.field_dict:
                #str_track = get_track_str(self.field_dict, field)
                str_track = get_track_str( self.field_dict.get_node(field) )
                #str_track = str( self.field_dict.get_node(field).track() ).replace(' ', '')
                track_list.append( str_track )
            else:
                #logging.warn("'%s' is not in self.field_dict" % field)
                track_list.append( "(-1,-1)" )
        return str.join(' | ', track_list)

    cpdef str tracks2line(self, str tracks):
    #cpdef str tracks2line(self, str tracks):
        cdef list field_list = []
        #cdef (int,int) numbers
        cdef list numbers
        cdef size_t node_id, length
        for track in tracks.split('|'):
            track = track.strip()
            if track:
                #field is form of "(id,length)")
                #numbers = ( field[1:-1].split(',') )
                #node_id = int(numbers[0])
                #length  = int(numbers[1])
                #field_list.append( self.field_dict.trie.suffix(node_id,length) )
                field_list.append( track2key(self.field_dict, track) )
            else:
                field_list.append( '' )
        return str.join(' ||| ', field_list)

    cdef __load(self):
        cdef long i
        cdef str line
        #cdef object rec
        cdef str src, trg
        cdef str srcKey
        #print(self.table_file)
        cdef str line_tracks
        cdef str src_tracks
        cdef str trg_tracks
        cdef str str_track_pair
        cdef str pair_tracks
        #cdef list rec_tracks
        cdef object node
        cdef str field

        for i, line in enumerate(progress.view(self.table_path, 'building trie of all fields')):
            #if i > 200000:
            #    break
            try:
                src = line.split('|||',1)[0].strip()
                self.add_fields(line)
                self.add_fields(self.format_src_key(src))
                if self.trg_key_enabled:
                    trg = line.split('|||',2)[1].strip()
                    self.add_fields(trg)
                    if trg.find('|COL|') >= 0:
                        for field in trg.split('|COL|'):
                            self.add_fields(field.strip())
            except Exception as e:
                logging.warn("file: %s, line: %s" % (self.table_path, i+1))
                logging.warn(e)
                raise e

        for i, line in enumerate(progress.view(self.table_path, 'building trie of all records')):
            try:
                line_tracks = self.line2tracks(line.strip())
                self.record_dict.update(line_tracks, 1)
            except Exception as e:
                logging.warn("file: %s, line: %s" % (self.table_path, i+1))
                logging.warn(e)
                raise e

        for node in progress.view(self.record_dict.nodes(), 'registering pair of (key,record)', max_count=len(self.record_dict)):
            try:
                line_tracks = node.key()
                line = self.tracks2line(line_tracks)
                src = line.split('|||',1)[0].strip()
                src_key = self.format_src_key(src)
                #self.add_key_and_node(src_key, node)
                self.add_key_and_node(self.src_record_dict, src_key, node)
                if self.trg_key_enabled:
                    trg = line.split('|||', 2)[1].strip()
                    #self.add_key_and_node(trg, node)
                    self.add_key_and_node(self.trg_record_dict, trg, node)
                    if trg.find('|COL|') >= 0:
                        for i, field in enumerate(trg.split('|COL|')):
                            if i >= len(self.trg_field_record_dicts):
                                self.trg_field_record_dicts.append( pycedar.dict(str) )
                            #self.add_key_and_node(field.strip(), node)
                            self.add_key_and_node(self.trg_field_record_dicts[i], field.strip(), node)
            except Exception as e:
                logging.warn("line_tracks: %s" % line_tracks)
                logging.warn("line: %s" % line)
                #logging.warn("src_key: %s" % src_key)
                logging.warn(e)
                raise e

    def __find_key(self, object key_record_dict, str key, bool force=True):
        cdef str line
        cdef str key_track
        cdef str pair_tracks
        cdef str record_track
        cdef str line_tracks

        key_track = self.line2tracks(key)
        if key_track.find('(-1,-1)') >= 0:
            return
        for pair_tracks in key_record_dict.find_keys(key_track,force=force):
            record_track = pair_tracks.split('|',1)[1].strip()
            line_tracks = track2key(self.record_dict, record_track)
            line = self.tracks2line(line_tracks)
            yield self.RecordClass(line)

    def find(self, str prefix, bool force=True):
        cdef str prefix_tracks
        cdef str line_tracks
        cdef str line

        prefix_tracks = self.line2tracks(prefix)
        for line_tracks in self.record_dict.find_keys(prefix_tracks, force=force):
            line = self.tracks2line(line_tracks)
            yield self.RecordClass(line)

    #def find(self, str key):
    #    cdef str line
    #    #cdef str str_tracks
    #    cdef str key_track
    #    cdef str pair_tracks
    #    cdef str record_track
    #    cdef str line_tracks

    #    if key:
    #        #str_tracks = self.line2tracks(key)
    #        key_track = self.line2tracks(key)
    #        if key_track.find('(-1,-1)') >= 0:
    #            return
    #        #for line in self.record_dict.find_keys(str_tracks, force=True):
    #        #    main_tracks = line.split('|||', 1)[1]
    #        #    yield self.RecordClass( self.tracks2line(main_tracks) )
    #        #for pair_tracks in self.key_record_dict.find_keys(key_track, force=True):
    #        for pair_tracks in self.src_record_dict.find_keys(key_track, force=True):
    #            record_track = pair_tracks.split('|',1)[1].strip()
    #            line_tracks  = track2key(self.record_dict, record_track)
    #            line = self.tracks2line(line_tracks)
    #            yield self.RecordClass( line )
    #    else:
    #        # empty key, find all records (without key)
    #        for line_tracks in self.record_dict.find_keys('', force=True):
    #            line = self.tracks2line(line_tracks)
    #            yield self.RecordClass( line )

    #cpdef find_src(self, str src):
        #return self.find(self.format_src_key(src))

    cpdef find_src(self, str src, force=True):
        return self.__find_key(self.src_record_dict, self.format_src_key(src), force=force)

    #cpdef find_trg(self, str trg):
    #    if not trg:
    #        raise KeyError("trg should not be empty")
    #    return self.find(trg)

    cpdef find_trg(self, str trg, object target_index=None, force=True):
        #if target_number >= 0:
        if isinstance(target_index,int):
            return self.__find_key(self.trg_field_record_dicts[target_index], trg, force=force)
        else:
            return self.__find_key(self.trg_record_dict, trg, force=force)

    #def find_trg(self, str trg):
    #    if self.trg_record_dict is None:
    #        raise LookupError('target key is not enabled, please init with Table(..., trg_key=True)')
    #    cdef str line
    #    cdef str str_tracks
    #    str_tracks = self.line2tracks(trg)

    #    if str_tracks == '(-1,-1)':
    #        return
    #    for line in self.trg_record_dict.find_keys(str_tracks, force=True):
    #        main_tracks = line.split('|||', 1)[1]
    #        yield self.RecordClass( self.tracks2line(main_tracks) )

    def __iter__(self):
        return self.find('')

    def __len__(self):
        return len(self.record_dict)

class MosesTable(Table):
    def __init__(self, table_path, **options):
        Table.__init__(self, table_path, records.MosesRecord, **options)

class TravatarTable(Table):
    def __init__(self, table_path, **options):
        Table.__init__(self, table_path, records.TravatarRecord, **options)

