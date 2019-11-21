import gf

DEBUG = False

BYTE_SIZE = 8
CHUNK_SIZE = BYTE_SIZE

class parity:
    def __init__(self, number_of_disk=8):
        self.F = gf.FField(number_of_disk)

    def compute_P(self,list_chunks):
        c = list_chunks[0]
        for x in list_chunks[1:]:
            c = c ^ x
        return c


    def compute_Q(self,list_chunks):
        c = list_chunks[0]
        for i in range(1,len(list_chunks)):
            c = c ^ self.F.Multiply(2**i, list_chunks[i]) 
        
        return c
            

    def recover_one_chunk_with_P(self,remaining_chunks, P_chunk):
        c = P_chunk
        for x in remaining_chunks:
            c = c ^ x 

        return c

    def recover_one_chunk_with_Q(self,all_disk_chunks, Q_chunk, missing_chunk_index):
        c = Q_chunk
        for i in range(0,len(all_disk_chunks)):
            if i == missing_chunk_index:
                continue

            c = c ^ self.F.Multiply(2**i, all_disk_chunks[i])

        return self.F.Multiply(self.F.Inverse(2**missing_chunk_index), c)


    def recover_two_chunk(self,all_disk_chunks, P_chunk, Q_chunk, missing_chunk_1, missing_chunk_2):
        A = P_chunk
        B = Q_chunk
        for i in range(0,len(all_disk_chunks)):
            if i in [missing_chunk_1, missing_chunk_2]:
                continue
            
            A = A ^ all_disk_chunks[i]
            B = B ^ self.F.Multiply(2**i, all_disk_chunks[i])

        D_1 = self.F.Multiply(self.F.Inverse(2**missing_chunk_1 ^ 2**missing_chunk_2), self.F.Multiply(2**missing_chunk_2, A) ^ B)
        D_2 = A ^ D_1
        return D_1,D_2
    


if (DEBUG):
    TEST_LIST = [0b11111111,0b11110101,0b11110011]
    print(TEST_LIST)

    P = (compute_P(TEST_LIST))
    print("P",P, type(P))
    Q = (compute_Q(TEST_LIST))
    print("Q",Q, type(Q))

    print("Recovered:",recover_one_chunk_with_P(TEST_LIST[:-1], P))
    print("Recovered:",recover_one_chunk_with_Q(TEST_LIST, Q, 1))

    TEST_LIST = [0b11111111,0,0]

    print("Recovered:",recover_two_chunk(TEST_LIST, P, Q, 1, 2))


