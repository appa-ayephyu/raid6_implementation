import os
import sys
import shutil
import parity
import struct
import time


class RAID6:
    ''' 
    This class can be used to simulate a RAID6 software implementation
    '''

    ###
    # Allow the user to define certains characteristics of the RAID6, like the CHUNK_SIZE
    # or the number of disk
    # It will also reinitialize any previous disk created
    ###
    def __init__(self, number_of_disk=8, chunk_size=128):
        self.PATH = 'disks/'
        self.NUMBER_OF_DISKS = number_of_disk    # Safe to modify
        self.BYTE_SIZE = 8
        self.CHUNK_SIZE = chunk_size       # Safe to modify

        self.current_index = 0      # Index where to write next
        self.current_disk_index = 0 # Disk where to write next

        self.P_INDEX =  self.NUMBER_OF_DISKS - 2    # Index of the P disk
        self.Q_INDEX =  self.NUMBER_OF_DISKS - 1    # Index of the Q disk

        self.ENFORCING_CHECK = True # Check the parity byte each read

        self.WRITING_INFO = 'b'

        if number_of_disk>8:
            self.WRITING_INFO='q'

        #name:[{index, disk, offset, length}, ...]
        self.FILES_INFO = {}        # Info to get the files accross multiples blocks

        #available_place
        self.ERASED_INFO = []       # Blocks erased and that can be reused

        self.DISKS_INFO = []        # Info on disk utilization

        self.parity = parity.parity(number_of_disk)

        # Removing old directory
        try:
            shutil.rmtree(self.PATH)
        except:
            pass
        for i in range(self.NUMBER_OF_DISKS):
            directory = "disk_" + str(i)
            if not os.path.exists(self.PATH + directory):
                os.makedirs(self.PATH + directory)

    ###
    # Simple function allowing to increase the disk index to know where to write next
    ###
    def increase_disk_index(self, ret=False):
        self.current_disk_index = (self.current_disk_index + 1) % (self.NUMBER_OF_DISKS - 2)

    ###
    # Simple function allowing to update the disk info to know if a block is 
    # full.
    ###
    def update_disk_info(self, index, disk_index, length):
        try:
            self.DISKS_INFO[index][disk_index] = length
        except:
            self.DISKS_INFO.append([0 for i in range(self.NUMBER_OF_DISKS)]) 
            self.DISKS_INFO[index][disk_index] = length

            

    def restore_parity(self, index_number):
        # Get chunk data from the index
        data, par = self.read_one_chunk(index_number,self_recovering=False)
        current_data = [[] for loop in range(self.CHUNK_SIZE)]
        for x in data:
            for i in range(len(x)):
                current_data[i].append(x[i])

        # Compute P and Q list on a byte to byte basis
        P = []
        Q = []
        for x in current_data:
            if len(x) > 0:
                P.append(self.parity.compute_P(x))
                Q.append(self.parity.compute_Q(x))

        self.update_disk_info(index_number, (self.P_INDEX + index_number) % self.NUMBER_OF_DISKS, len(P))
        self.update_disk_info(index_number, (self.Q_INDEX + index_number) % self.NUMBER_OF_DISKS, len(Q))

        # Store the parity
        with open(self.PATH + 'disk_' + str((self.P_INDEX + index_number) % self.NUMBER_OF_DISKS) + '/' + str(index_number), 'wb') as f:
            for x in P:
                f.write(struct.pack(self.WRITING_INFO, x - (pow(2,self.NUMBER_OF_DISKS)//2)))
        with open(self.PATH + 'disk_' + str((self.Q_INDEX + index_number) % self.NUMBER_OF_DISKS) + '/' + str(index_number), 'wb') as f:
            for x in Q: 
                f.write(struct.pack(self.WRITING_INFO, x - (pow(2,self.NUMBER_OF_DISKS)//2))) #for example -128 to 128 for 2^8 (8 disks case)


    ###
    # Write data to RAID6 disks with the associated name
    # Will create a temporary file in disks/
    ###
    def write_data(self, data, name):
        data_as_bytes = str.encode(data)

        with open(self.PATH + 'temp', 'wb') as f:
            f.write(data_as_bytes)

        return self.write_data_from_file(self.PATH + 'temp', name)
    
    ###
    # Write data to RAID 6 with the associated name from the file
    # If we want to write the file to a specific chunk, give a list in chunk_to_write
    # Offset allow to write from a certain part of the file (update)
    ###
    def write_data_from_file(self, file, name, chunk_to_write=[], offset=0):
        stat_info = os.stat(file)
        size = stat_info.st_size
        
        # Determining if the data can be write on previously used data
        if len(chunk_to_write) == 0:
            places_to_write = []
            for x in self.ERASED_INFO[:]:
                places_to_write.append(x)
                self.ERASED_INFO.remove(x)
                size -= x['length']
                if size <= 0:
                    break
            if size > 0:
                places_to_write.append({'index': self.current_index, 'disk': self.current_disk_index, 'offset': 0, 'length': size})
        else:
            places_to_write = chunk_to_write

        # Opening the input file
        with open(file, "rb") as in_file:
            # Setting the offset accordingly
            if offset > 0:
                in_file.read(offset)

            # Reading each place to write the file to
            for place_to_write in places_to_write:
                # Loading position data
                starting_index = place_to_write['index']
                starting_disk = place_to_write['disk']
                starting_offset = place_to_write['offset']
                index = place_to_write['index']
                disk = place_to_write['disk']


                lenght_to_write = place_to_write['length']
                lenght_data = 0

                # Determining if we're going to write mid-disk
                heading_offset = 0
                if starting_offset > 0:
                    lenght_data = 0
                    while lenght_data + self.CHUNK_SIZE <= starting_offset:
                        lenght_data += self.CHUNK_SIZE
                        disk = (disk + 1) 
                        if disk == self.P_INDEX:
                            index += 1
                            disk = 0
                    heading_offset = starting_offset - lenght_data

                # Determining if we're writing on new blocks which will have to be properly created
                live = False
                if index == self.current_index and disk == self.current_disk_index:
                    live = True

                # Loading data if we have an offset
                lenght_data = starting_offset
                if heading_offset > 0:
                    chunk_data = []
                    with open(self.PATH + 'disk_' + str((disk + index) % self.NUMBER_OF_DISKS) + '/' + str(index), 'rb') as f:
                        for _ in range(heading_offset):
                            chunk_data.append(struct.unpack("b", f.read(1))[0] + 128)
                else:
                    chunk_data = []

                
                ### 
                # MAIN WRITING LOOP 
                ###
                while lenght_data < lenght_to_write:
                    # Reading the values and converting them to int
                    value = in_file.read(1)
                    value = int.from_bytes(value, byteorder='big')
                    chunk_data.append(value)
                    lenght_data += 1

                    # Writing the data to one disk
                    if (len(chunk_data) == self.CHUNK_SIZE):
                        with open(self.PATH + 'disk_' + str((disk + index) % self.NUMBER_OF_DISKS) + '/' + str(index), 'wb') as f:
                            for j in range(self.CHUNK_SIZE):
                                x = chunk_data[j]
                                f.write(struct.pack(self.WRITING_INFO, x - (pow(2,self.NUMBER_OF_DISKS)//2))) # write an int                            
                        
                        # Updating RAID6 writing data
                        self.update_disk_info(index, (disk + index) % self.NUMBER_OF_DISKS, self.CHUNK_SIZE)
                        if live:
                            self.increase_disk_index()
                        disk += 1
                        chunk_data = []
                        if disk == self.P_INDEX:
                            self.restore_parity(index)
                            if live:
                                self.current_index += 1
                            index += 1
                            disk = 0
                    
                # If there is a uncomplete chunk, write trailing 0 to have proper parity calculation
                if len(chunk_data) > 0:
                    with open(self.PATH + 'disk_' + str((index + disk) % self.NUMBER_OF_DISKS) + '/' + str(index), 'wb') as f:
                        for j in range(len(chunk_data)):
                            x = chunk_data[j]
                            f.write(struct.pack(self.WRITING_INFO, x - (pow(2,self.NUMBER_OF_DISKS)//2))) # write an int

                        for j in range(len(chunk_data), self.CHUNK_SIZE):	
                            f.write(struct.pack(self.WRITING_INFO, 0 - (pow(2,self.NUMBER_OF_DISKS))//2)) # write an int	
                    self.update_disk_info(self.current_index, (index + disk) % self.NUMBER_OF_DISKS, len(chunk_data))
                    if live:
                        self.increase_disk_index()
                    disk += 1
                    if disk == self.P_INDEX:
                        self.restore_parity(index)
                        if live:
                            self.current_index += 1
                        index += 1
                        disk = 0
                
                if disk > 0:
                    self.restore_parity(index)


                # Write the file info to the FILES_INFO index
                try:
                    self.FILES_INFO[name].append({'index':starting_index, 'disk':starting_disk, 'offset':0, 'length':lenght_data})
                except:
                    self.FILES_INFO[name] = [{'index':starting_index, 'disk':starting_disk, 'offset':0, 'length':lenght_data}]

        return True

    ###
    # Determining if an index is the P_index since P is store in a cyclic way
    ###
    def is_P_index(self, chunk_index, disk_index):
        if (chunk_index + self.P_INDEX) % self.NUMBER_OF_DISKS == disk_index:
            return True
        return False

    ###
    # Determining if an index is the Q_index since Q is store in a cyclic way
    ###
    def is_Q_index(self, chunk_index, disk_index):
        if (chunk_index + self.Q_INDEX) % self.NUMBER_OF_DISKS == disk_index:
            return True
        return False
    
    ###
    # Give the actual index of a disk since disk are stored in a cyclic way
    ###
    def actual_disk_index(self, index, disk):
        return (disk + (index % self.NUMBER_OF_DISKS) + self.NUMBER_OF_DISKS) % self.NUMBER_OF_DISKS

    ###
    # Read one index (all the disks), readying data and recovering disk loss
    # Some disks can be excluded while recovering data
    # Self recovering can be turned off in order to accomodate reading incomplete index
    ###
    def read_one_chunk(self, chunk_index, exclude=[], already_recovered=False, self_recovering=True):
        # If trying to read out of bounds indexes
        if chunk_index > self.current_index:
            return False
        data = [[] for loop in range(self.NUMBER_OF_DISKS - 2)]
        p = []
        q = []
        failed = []

        ### MAIN READING LOOP ###
        for i in range(self.NUMBER_OF_DISKS):
            # Ignoring excluded disks
            if (chunk_index + i) % self.NUMBER_OF_DISKS in exclude:
                continue
            try:
                # Reading and storing data in lists
                with open(self.PATH + 'disk_' + str((chunk_index + i) % self.NUMBER_OF_DISKS) + '/' + str(chunk_index), 'rb') as f:
                    for _ in range(self.CHUNK_SIZE):
                        if self.WRITING_INFO=='b':
                            readbyte=1
                        else:
                            readbyte=8
                        try:
                            # since parity P and Q when using larger configurations set than 6+2 are more than 1 byte of data, we use 'long long int' which is 'q' for struct.pack/ unpack
                            # thus we read by f.read(8) since 'q' takes 8 bytes of space.
                            if i % self.NUMBER_OF_DISKS == self.P_INDEX:
                                p.append(struct.unpack(self.WRITING_INFO, f.read(readbyte))[0] + (pow(2,self.NUMBER_OF_DISKS)//2))
                            elif i % self.NUMBER_OF_DISKS == self.Q_INDEX:
                                q.append(struct.unpack(self.WRITING_INFO, f.read(readbyte))[0] + (pow(2,self.NUMBER_OF_DISKS)//2))
                            else:
                                data[i].append(struct.unpack(self.WRITING_INFO, f.read(readbyte))[0] + (pow(2,self.NUMBER_OF_DISKS)//2))
                        except Exception as e: 
                            break
            
            # If a disk fails logging it
            except Exception as e: 
                #print(e)
                if self_recovering and self.DISKS_INFO[chunk_index][(chunk_index + i) % self.NUMBER_OF_DISKS] > 0:
                    failed.append((chunk_index + i) % self.NUMBER_OF_DISKS)

        # If a disk have failed and self recovery activated, trying to recover it
        if len(failed) > 0 and self_recovering: 
            if self.ENFORCING_CHECK and len(exclude) == 0:
                if not already_recovered:            
                    print("[!] Error disk:",failed,"; Attempting recovery ...")
                    self.recovering_disks(failed)
                    return self.read_one_chunk(chunk_index, exclude, True)
                else:
                    raise IOError("Unrecoverable error")

                if p != self.parity.compute_P(data) or q != self.parity.compute_Q(data):
                    raise IOError("Error")
                
        # Disk successfully recovered
        if already_recovered:
            print("[✓] Error recovered !")
        return data, (p,q)

    ###
    # Read data to console given an index, disk and length to read
    # Not supposed to be used by end-user
    ###
    def read_data(self, starting_index, starting_disk, length):
        final_data = []
        local_index = starting_index

        i = 0
        # Read data from the right disk
        data, par = self.read_one_chunk(local_index)
        data = data[starting_disk:]
        i += self.CHUNK_SIZE * (len(data))
        final_data.extend(data)
        local_index += 1

        # While data to be read
        while i < length:
            data, par = self.read_one_chunk(local_index)
            i += self.CHUNK_SIZE * (self.NUMBER_OF_DISKS - 2)
            final_data.extend(data)
            local_index += 1
        
        original_data = ""
        i = 0
        for chunk_data in final_data:
            for x in chunk_data:
                original_data += chr(x)
                i += 1
                if i >= length:
                    break
            if i >= length:
                    break

        return original_data


    ###
    # Read data to a file given an index, disk and length to read
    # Not supposed to be used by end-user
    # Data can be add at the end of the file
    ###
    def read_data_to_file(self, file, starting_index, starting_disk, length, add=False):
        print("file", file, "starting index", starting_index, "length", length)
        local_index = starting_index

        # Lenght of data read
        i = 0 

        # Writing method to write at the end of the file
        writing_method = "wb"
        if add:
            writing_method = "ab"

        # Opening the file
        with open(file, writing_method) as out_file:
            data, par  = self.read_one_chunk(local_index)

            ## Starting at the right disk
            for j in range(starting_disk, len(data)):
                chunk_data = data[j]

                if (i + len(chunk_data) <= length):
                    size_readable = self.DISKS_INFO[local_index][self.actual_disk_index(local_index, j)]
                    chunk_data = chunk_data[:size_readable]
                    i += len(chunk_data[:size_readable])
                    out_file.write(bytes(chunk_data[:size_readable]))
                else:
                    out_file.write(bytes(chunk_data[:length - i]))
                    i = length
                    break

            
            local_index += 1

            # While we have data to read, write them to disk
            while i < length:
                data, par  = self.read_one_chunk(local_index)
                for j in range(len(data)):
                    chunk_data = data[j]
                    if (i + len(chunk_data) <= length):
                        size_readable = self.DISKS_INFO[local_index][self.actual_disk_index(local_index, j)]
                        chunk_data = chunk_data[:size_readable]
                        i += len(chunk_data[:size_readable])
                        out_file.write(bytes(chunk_data[:size_readable]))
                    else:
                        out_file.write(bytes(chunk_data[:length - i]))
                        i = length
                        break
                local_index += 1

        return True


    ###
    # Allow to recover up to 2 deleted disks
    # Use the parity file to do all the computations
    ###
    def recovering_disks(self, disks_number):
        # Recreate the folder
        for i in disks_number:
            try:
                os.makedirs("disks/disk_" + str(i))
            except:
                pass
                
        # One disk recovery case
        if len(disks_number) == 1:
            disk_number = disks_number[0]
            index = 0
            max_index = self.current_index
            #if current disk index is 0 means the last index is the largest index with the stored data under this resepective file name
            if self.current_disk_index  == 0:
                max_index -= 1

            # Recovering all the indexes
            while index <= max_index:
                data, par = self.read_one_chunk(index, disks_number)

                P,Q = par
                data_packed = [[] for _ in range(self.CHUNK_SIZE)]

                for x in data:
                    for i in range(len(x)):
                        data_packed[i].append(x[i])
                
                # Use case 1 when data is corrupted
                if P != [] and Q != []:
                    dat = [] 
                    for i in range(len(data_packed)):
                        dat.append(self.parity.recover_one_chunk_with_P(data_packed[i], P[i]))

                    try:
                        if self.DISKS_INFO[index][disk_number] < self.CHUNK_SIZE:
                            dat = dat[:self.DISKS_INFO[index][disk_number]]
                    except:
                        return

                    with open(self.PATH + 'disk_' + str(disk_number) + '/' + str(index), 'wb') as f:
                        for value in dat:
                            f.write(struct.pack(self.WRITING_INFO, value - (pow(2,self.NUMBER_OF_DISKS)//2)))

                # Use case 2 when P parity is corrupted
                elif P == []:
                    with open(self.PATH + 'disk_' + str(disk_number) + '/' + str(index), 'wb') as f:
                        for i in range(len(data_packed)):
                            p = self.parity.compute_P(data_packed[i])
                            f.write(struct.pack(self.WRITING_INFO, p - (pow(2,self.NUMBER_OF_DISKS)//2)))
                
                # Use case 3 when Q parity is corrupted
                elif Q == []:
                    with open(self.PATH + 'disk_' + str(disk_number) + '/' + str(index), 'wb') as f:
                        for i in range(len(data_packed)):
                            q = self.parity.compute_Q(data_packed[i])
                            f.write(struct.pack(self.WRITING_INFO, q - (pow(2,self.NUMBER_OF_DISKS)//2)))
                index += 1

        ## Two disk recovery case
        elif len(disks_number) == 2:
            disk_number = min(disks_number[0],disks_number[1])
            disk1_number = disks_number[0]
            disk2_number = disks_number[1]

            i = 0
            max_index = self.current_index

            #if current disk index is 0 means the last index is the largest index with the stored data under this resepective file name
            if self.current_disk_index ==0:
                max_index -=1
            while i <= max_index:
                data, par = self.read_one_chunk(i, disks_number)
                P,Q = par

                data_packed = [[] for _ in range(self.CHUNK_SIZE)]

                for k in range(self.CHUNK_SIZE):
                    for j in range(len(data)):
                        try:
                            data_packed[k].append(data[j][k])
                        except:
                            data_packed[k].append(0)

                # Use case 1 where the parity P and Q are corrupted
                if P == [] and Q == []:
                    self.restore_parity(i)

                # Use case 2 where data chunks are corrupted
                elif P != [] and Q != []:
                    #Get current position of the data in the list
                    actual_index1 = (disk1_number - (i % self.NUMBER_OF_DISKS) + self.NUMBER_OF_DISKS) % self.NUMBER_OF_DISKS
                    actual_index2 = (disk2_number - (i % self.NUMBER_OF_DISKS) + self.NUMBER_OF_DISKS) % self.NUMBER_OF_DISKS
                    with open(self.PATH + 'disk_' + str(disk1_number) + '/' + str(i), 'wb') as f1, open(self.PATH + 'disk_' + str(disk2_number) + '/' + str(i), 'wb') as f2:
                        for k in range(len(data_packed)):   
                            a,b = self.parity.recover_two_chunk(data_packed[k], P[k], Q[k], actual_index1, actual_index2)
                            f1.write(struct.pack(self.WRITING_INFO, a - (pow(2,self.NUMBER_OF_DISKS)//2)))
                            f2.write(struct.pack(self.WRITING_INFO, b - (pow(2,self.NUMBER_OF_DISKS)//2)))
                
                # Use case 3 when parity P and a data chunk is corrupted
                elif P == [] :
                    data_index = disk1_number
                    p_index = disk2_number
                    if self.is_P_index(i, disk1_number):
                        data_index = disk2_number
                        p_index = disk1_number

                    with open(self.PATH + 'disk_' + str(data_index) + '/' + str(i), 'wb') as f1, open(self.PATH + 'disk_' + str(p_index) + '/' + str(i), 'wb') as f2:
                        #Get current position of the data in the list
                        actual_index = int((data_index - (i % self.NUMBER_OF_DISKS) + self.NUMBER_OF_DISKS) % self.NUMBER_OF_DISKS)
                        #data.insert(actual_index, 0)
                        for k in range(len(data_packed)):
                            data_packed[k][actual_index] = self.parity.recover_one_chunk_with_Q(data_packed[k], Q[k], actual_index)
                            f1.write(struct.pack(self.WRITING_INFO, data_packed[k][actual_index] - (pow(2,self.NUMBER_OF_DISKS)//2)))
                            f2.write(struct.pack(self.WRITING_INFO, self.parity.compute_P(data_packed[k]) - (pow(2,self.NUMBER_OF_DISKS)//2)))
                        
                # Use case 4 when Parity Q and a data chunk is corrupted
                elif Q == [] :
                    data_index = disk1_number
                    q_index = disk2_number
                    if self.is_Q_index(i, disk1_number):
                        data_index = disk2_number
                        q_index = disk1_number

                    with open(self.PATH + 'disk_' + str(data_index) + '/' + str(i), 'wb') as f1, open(self.PATH + 'disk_' + str(q_index) + '/' + str(i), 'wb') as f2:
                        #Get current position of the data in the list
                        actual_index = int((data_index - (i % self.NUMBER_OF_DISKS) + self.NUMBER_OF_DISKS) % self.NUMBER_OF_DISKS)
                        for k in range(len(data_packed)):
                            data_packed[k][actual_index] = self.parity.recover_one_chunk_with_P(data_packed[k], P[k])
                            f1.write(struct.pack(self.WRITING_INFO, data_packed[k][actual_index] - (pow(2,self.NUMBER_OF_DISKS)//2)))
                            f2.write(struct.pack(self.WRITING_INFO, self.parity.compute_Q(data_packed[k]) - (pow(2,self.NUMBER_OF_DISKS)//2)))
                        

                i += 1

    ###
    # Deleting data based on their respective name in FILES_INFO
    # Data will still be on disk but can be rewritten on
    ###
    def delete_data(self, name):
        try:
            position_info = self.FILES_INFO.pop(name)
            for x in position_info:
                self.ERASED_INFO.append(x)

            return True
        except:
            return False

    ###
    # Print FILES_INFO
    ###
    def printfileinfo(self):
        for x in self.FILES_INFO:
            print(self.FILES_INFO[x])
    ###
    # Update the data stored based on their respective name in FILES_INFO
    # Will compare data to only store changed data
    # Stored data different from update are appended to ERASED_INFO
    ###
    def update_data_from_file(self, filename, name):
        stat_info = os.stat(filename)
        total_size = stat_info.st_size

        '''
        saved_data = self.get_data_from_name(name)
        similar_size = 0
        with open(filename, "rb") as in_file:
            while similar_size < total_size:
                try:
                    data = in_file.read(1)
                    if data == str.encode(saved_data[similar_size]):
                        similar_size += 1
                    else:
                        break
                except:
                    break
        '''
        file_info = self.FILES_INFO[name]
        total_size_saved = 0
        for x in file_info:
            total_size_saved += x['length']

        
        #Getting the place to write
        #size_to_write = total_size - similar_size
        size_to_write = total_size
        similar_size = 0
        similar_ = similar_size
        
        writing_to = []
        totally_written = False
        already_written = 0
        for x in file_info[:]:
            #Removing trailing data blocks
            if totally_written:
                file_info.remove(x)
                self.ERASED_INFO.append(x)
            similar_ -= x['length']
            if similar_ < 0:
                a = x.copy()
                file_info.remove(x)
                added_size_to_fill = 0

                if a['length'] % self.CHUNK_SIZE != 0:
                    added_size_to_fill = a['length']
                    a['length'] = a['length'] + (self.CHUNK_SIZE - a['length'] % self.CHUNK_SIZE)
                    added_size_to_fill = a['length'] - added_size_to_fill
                if similar_ + a['length'] > 0:
                    a['offset'] = 0 

                
                already_written += a['length'] - a['offset']
                if a['length'] - a['offset'] >= size_to_write:
                    totally_written = True
                    old_size = a['length']
                    a['length'] = size_to_write + similar_ + a['length'] - added_size_to_fill
                    #freeing space
                    index = a['index']
                    disk = a['disk']
                    data_w = 0
                    while data_w < a['length']:
                        data_w += self.CHUNK_SIZE
                        disk = (disk + 1) 
                        if disk == self.P_INDEX:
                            index += 1
                            disk = 0
                    self.ERASED_INFO.append({'index':index, 'disk':disk, 'offset':0, 'length':old_size - data_w})

                writing_to.append(a)

        if already_written < size_to_write:
            writing_to.append({'index':self.current_index, 'disk':self.current_disk_index, 'offset':0, 'length':size_to_write - already_written})
        
        print("writing_to", writing_to)
        print("offset", similar_size)
        return self.write_data_from_file(filename, name, chunk_to_write=writing_to, offset=similar_size)

    ###
    # Get the stored data from their respective name in FILES_INFO
    ###
    def get_data_from_name(self, name):
        try:
            position_info = self.FILES_INFO[name]
            data = ""
            for x in position_info:
                data += self.read_data(x['index'], x['disk'], x['length'])
            return data
        except:
            return False
    
    ###
    # Write the stored data to a file from their respective name in FILES_INFO
    ###
    def print_data_to_file(self, filename, name):
        try:
            position_info = self.FILES_INFO[name]
            success = self.read_data_to_file(filename, position_info[0]['index'], position_info[0]['disk'], position_info[0]['length'])
            for x in position_info[1:]:
                success = success and self.read_data_to_file(filename, x['index'], x['disk'], x['length'], add=True)
            return success
        except Exception as e: 
            print(e)
            return False


