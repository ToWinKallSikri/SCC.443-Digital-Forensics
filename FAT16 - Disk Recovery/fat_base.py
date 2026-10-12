import sys
import struct

class FAT :

    def getSector( self, sector: int ) -> bytes :
        self.fatFile.seek( sector * self.BytsPerSec )
        return self.fatFile.read( self.BytsPerSec )
    
    def __init__( self, imageFileName: str ) -> None :
        self.fatFile = open( imageFileName, 'rb' )
        self.BytsPerSec = 512 # We assume 512 bytes until we know better
        block0 = self.getSector( 0 ) # Read metadata from first sector

        # Unpack filesystem metadata
        self.jmpBoot, self.OemName, self.BytsPerSec, self.SecPerClus, \
        self.ReservdSecCount, self.NumFATs, self.RootEntCnt, \
        self.TotSec16, self.Media, self.FATSz16, self.SecPerTrk, \
        self.NumHeads, self.HiddSec, self.TotSec32, self.FATSz32 = \
        struct.unpack( '<3s8sHBHBHHBHHHLLL', block0[ : 40 ] )

        # Calculate some useful values -- See Microsoft Whitepaper
        self.RootDirSectors = int(
        ( self.RootEntCnt * 32 + self.BytsPerSec - 1 ) /
        self.BytsPerSec )
        self.FirstDataSector = self.ReservdSecCount + (
        self.NumFATs * self.FATSz16 ) + self.RootDirSectors
        self.DataSec = self.TotSec16 - ( self.ReservdSecCount +
        ( self.NumFATs * self.FATSz16 ) + self.RootDirSectors )
        self.CountOfClusters = int( self.DataSec / self.SecPerClus )
        self.FATStart = self.ReservdSecCount # Sectors; and 1st root sector is:
        self.RootDirStart = self.ReservdSecCount + self.NumFATs * self.FATSz16

    def __str__( self ) -> str :

        return f'\n{self.BytsPerSec = } bytes \
                 \n{self.SecPerClus = } sectors \
                 \n{self.ReservdSecCount = } sectors \
                 \n{self.NumFATs = } \
                 \n{self.RootEntCnt = } entries \
                 \n{self.RootDirStart = } cluster \
                 \n{self.TotSec16 = } sectors \
                 \n{self.FATSz16 = } sectors \
                 \n{self.HiddSec = } sectors\n\n' \
                                      


    def close( self ) -> None :

        self.fatFile.close( )
        
    """
    Function to read the entries of the table, given a cluster number and a the position of the table in the image
    The function can adapt to different FAT storing mechanisms, since its cluster entry bytes number are variable
    """
    def entry_reader_in_fat(self, c, entry_bytes, fat_n):
        fat_pos = 0
        # Getting the position of the first FAT in bytes
        if fat_n == 1:
            fat_pos = self.FATStart * self.BytsPerSec
        if fat_n == 2:
            fat_pos = (self.FATStart + self.FATSz16) * self.BytsPerSec
        # Byte offset in FAT #1 or FAT #2 to get to the FAT entry (following the rule that each cluster index
        # means that its contents are (c * entry size in byte) bytes far in the FAT)
        entry_offset = fat_pos + c * entry_bytes
        self.fatFile.seek(entry_offset)
        # Slice the first two bytes in the FAT in order to get the next cluster from the cluster number given in input (int)
        return int.from_bytes(self.fatFile.read(entry_bytes), 'little')
    

    """
    Function to reach and read the desired cluster in the data area, given a cluster number (int)
    """
    def get_cluster(self, c):
        # Move to the Data Area and stop at the desired cluster position
        offset_bytes = (self.FirstDataSector + (c-2) * self.SecPerClus) * self.BytsPerSec
        # Begin the reading at the desired position
        self.fatFile.seek(offset_bytes)
        # Read the bytes of the cluster, considering the number of sectors and their size
        return self.fatFile.read(self.SecPerClus * self.BytsPerSec)
    

    """
    Function to read the root directory
    """
    def get_root_dir(self):
        
        dir_entries = []

        # Calculate the offset of the root directory (beginning)
        root_start = self.RootDirStart * self.BytsPerSec

        # Calculate length in bytes
        root_dir_length = self.RootDirSectors * self.BytsPerSec

        
        # Go to the begininning of the root folder
        self.fatFile.seek(root_start)

        # Read the directory and split in chunks
        root_bytes = self.fatFile.read(root_dir_length)
        # Printing to check if the direcotry is empty
        print("RootDirStart:", self.RootDirStart)
        print("RootDirSectors:", self.RootDirSectors)
        print("First 64 bytes of root dir:", root_bytes[:64])
        # Checking if there are any bytes that are not 0 in the root direcotry
        non_zero = [b for b in root_bytes if b != 0]
        print("Non-zero bytes in root:", len(non_zero))

        # Splitting in 32 bytes chunks
        for i in range(0, root_dir_length, 32):
            # root_bytes indexing from i to i+32, in order to be able to group the needed number of bytes to select information individually
            entry = root_bytes[i : i+32]
            # Skimming through the chunk of bytes, first checking the inital byte
            first_byte = entry[0]
            # If the first byte is 0x00 the directory ends, so it must stop
            if first_byte == 0x00:
                break
            # If the first byte is 0xE5, it means that the entry was deleted
            if first_byte == 0xE5:
                continue
            # Grouping the bytes to get the information. Each part of the chunk of bytes has a dedicated length, the first is the name
            # The name is 8+3 characters - 11 bytes
            name_raw = entry[0:11]          
            # Attributes at the 11th byte 
            attr = entry[11]
            # Starting cluster of the file (16-bit field called FstClusLO in the FAT spec)
            first_cluster_low = int.from_bytes(entry[26:28], "little")
            # Size of the file
            size = int.from_bytes(entry[28:32], "little")
            # root_bytes rearrangement in a dictionary for better usability
            entry_dict = {
                "raw": entry,
                "name_raw": name_raw,
                "attr": attr,
                "first_cluster": first_cluster_low,
                "size": size,
            }

            dir_entries.append(entry_dict)
        
        return dir_entries
    

    """
    Function for reading the file allocation tables (fat #1 or #2)
    """
    def file_alloc_table(self, n):
        # Init byte array
        b = [bytes]
        if n == 1:
            # The first sector position of the file allocation table
            fat1_offset = self.FATStart * self.BytsPerSec
            # Calculating the size in bytes of the table
            fat1_length = self.FATSz16 * self.BytsPerSec
            # Moving to that position in the image
            self.fatFile.seek(fat1_offset)
            # Reading the full length of the table and returing its data
            b = self.fatFile.read(fat1_length)
            return b
        
        if n == 2:
            # The first sector position of the file allocation table
            fat2_offset = (self.FATStart + self.FATSz16) * self.BytsPerSec
            # Calculating the size in bytes of the table
            fat2_length = self.FATSz16 * self.BytsPerSec
            # Moving to that position in the image
            self.fatFile.seek(fat2_offset)
            # Reading the full length of the table and returing its data
            b = self.fatFile.read(fat2_length)
            return b
        
        else:
            return b
