from fat_base import FAT
import os

# Resolving the path relative to this script's directory
img_path = os.path.join(os.path.dirname(__file__), 'fat16-37078169-38.img')
fat = FAT(img_path)

# Max value to be reached if looping in the image (avoid out of bound)
max = fat.CountOfClusters + 1

"""
Function made to find the next cluster of a given one in order to build the chain of clusters of a specific file
"""
def find_next(start):
    # Init a list
    l = []
    # First cluster in input
    c = start
    # Set to check against the next clusters to verify that there is no collision with the previous ones
    visited = set()

    while True: 
        # If next cluster was already visited return
        if c in visited: 
            return l 
        # Add visited clusters in the control set
        visited.add(c)
        # Add new cluster number to build the chain of clusters
        l.append(c)
        # Search the cluster number in the FAT
        tmp = fat.entry_reader_in_fat(c, 2, 1)
        # Verify cluster number value - stop conditions: end of the chain, empty cluster or out of bound  
        if tmp >= 0xFFF8 or tmp == 0 or tmp >= max:   
            return l 
        else:
            # Pick latest cluster number, cycle again until return conditions met    
            c = tmp  


"""
Read the chain of cluster in the data area (bytes to string)
"""
def read_chain(l):
    # Init a set to group the data from the clusters
    file_bytes = bytearray()

    for c in l:
        # Call get_cluster() function to get the actual bytes from the image
        tmp = fat.get_cluster(c)
        file_bytes.extend(tmp)

    return bytes(file_bytes)


"""
Function to decode the name of the file 
"""
def decode_name(name_raw: bytes) -> str:
    # File name extraction, white space removed
    name = name_raw[0:8].decode('ascii', errors='ignore').rstrip()
    # File extention,white space removed
    ext = name_raw[8:11].decode('ascii', errors='ignore').rstrip()
    # If there is an extention, concatenate the strings with a dot to construct the complete filename
    if ext:
        return f"{name}.{ext}"
    else:
        return name


"""
Function to read the content of the root direcotry
"""
def read_root_content():
    if not root_dir:
        print('Root directory is empty - possibly wiped')

    # Iterate the dictionaries (files) in the root directory
    for entry in root_dir:
        first_cluster = entry["first_cluster"]
        size = entry["size"]
        attrib = entry["attr"]
        name = decode_name(entry["name_raw"])
        # If the 11th bit is 0x10, it is a directory
        is_dir = (attrib & 0x10) != 0
        if is_dir:
            # At the moment, skip sub directory
            continue  

        if first_cluster == 0:
            continue  
        # Build the chain of clusters 
        chain = find_next(first_cluster)
        # Read the data from the cluster chain, bytes 
        bytes_data = read_chain(chain)
        # Based on the size, truncate to extract only content related to the root directory
        # Since the get_root_dir() function, showed that the direcotry is empty, the file_bytes are not printed
        # they would be simply zeros.
        file_bytes = bytes_data[:size]
        # If there are entries in the root dir they can be printed
        print(f"{name:20} | Cluster: {first_cluster:6} | Size: {size:10} | Chain Length: {len(chain):4}")


"""
Function to create all the chain of clusters, since the root directory is empty
"""
def create_chains():
    # Init the data structure that will hold the data
    chains = {}
    # The cluster number starts from 2 in FAT16
    i = 2
    # Iterate until reching out of bound limit
    while i <= max:
        # Search cluster in FAT 
        entry = fat.entry_reader_in_fat(i, 2, 1)

        if entry == 0:
            i += 1
            continue
        # Build the chain if the conditions are not met yet
        chains[i] = find_next(i)
        # Iterate every cluster number until reaching the limit
        i += 1

    return chains


"""
Function to check and measure eventual differences between the two FAT
"""
def check_fat_differences():
    fat1 = fat.file_alloc_table(1)
    fat2 = fat.file_alloc_table(2)
    if fat1 == fat2:
        print("Both FATs are the same.")
    else:
        print("Warning: Corruption may be occurred.")


"""
Function to save the recovered chains into a specific folder, mapping them to their original 
names and extensions by parsing recovered orphaned directories.
"""
def decode_recovered_chains(chains):
    # Read the chains' raw data, looking for metadata
    file_metadata = {}
    dirs_numb = 0
    sub_dirs = 0
    for ch in chains:
        # Retrieve the actual bytes reading them from the data area,using the cluster numbers in the chain
        raw_data = read_chain(ch)
        # Check if the chain is a directory (starts with standard '.' entry: b'.          \x10')
        # 11 bytes long - 8.3 naming format - \x10 is the 12th byte,  the attribute that flags
        # if the cluster chain is a directory
        if raw_data.startswith(b'.          \x10'):
            # Update the directory number counter
            dirs_numb += 1
            # Parse the 32-byte chunks of this directory
            for i in range(0, len(raw_data), 32):
                chunk = raw_data[i : i + 32]
                # If chunk is less than 32 bytes or is empty, skip
                if len(chunk) < 32 or chunk[0] == 0x00:
                    break 
                # Skip deleted files (0xE5) and Long File Names attributes (0x0F)
                if chunk[0] == 0xE5 or chunk[11] == 0x0F:
                    continue
                # Retrieve file name from chunk's first 11 bytes
                file_name = decode_name(chunk[0:11])
                # Check if it is a sub-directory
                is_dir = (chunk[11] & 0x10) != 0
                # Update the subdirectory counter
                if is_dir:
                    sub_dirs += 1
                # Get the first cluster of the file
                first_cluster = int.from_bytes(chunk[26:28], "little")
                # Record file size
                size = int.from_bytes(chunk[28:32], "little")
                
                # Keep valid records of known name and size, skipping empty clusters
                # and navigation links ('.' , '..')
                if first_cluster != 0 and file_name not in ['.', '..']:
                    file_metadata[first_cluster] = {
                        "name": file_name,
                        "size": size,
                        "is_dir": is_dir
                        }

    print(f"Found {dirs_numb} orphaned directory chains and {sub_dirs} sub-directories")
    # Returning a dictionary with the metadata, flagging directories, this way they are skipped
    # in the next process
    return file_metadata            
    
"""
Function to save the actual bytes to single files, with their specific extensions
"""
def save_files_from_chains(chains, file_metadata, output_folder = "RecoveredFiles" ):

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    # Using the retrieved metadata, now files can be saved in the RecoveredFiles folder
    counter = 0
    for ch in chains:
        start_cluster = ch[0]
        
        # When all the metadata is available (name, extension, size)
        if start_cluster in file_metadata:
            md = file_metadata[start_cluster]
            
            # Skip sub-dirs structural data, only their files are getting saved
            if md["is_dir"]:
                continue
            
            file_name = md["name"]
            file_size = md["size"]
            # Retrieve the actual bytes reading them from the data area,using the cluster numbers in the chain
            raw_data = read_chain(ch)
            # Truncate the file using its provided size to avoid padding
            file_bytes = raw_data[:file_size]
            
            out_path = os.path.join(output_folder, file_name)
            with open(out_path, "wb") as f:
                f.write(file_bytes)
                
            print(f"Saved: {file_name:20} | Cluster: {start_cluster:6} | Size: {file_size:10} bytes")
            counter += 1
            
        else:
            # When chain of clusters has no metadata, it is probably an orphane fragment data
            # therefore, it can be skipped
            pass
            
    print(f"Successfully saved {counter} files.")




"""
In sequence, several functions are run:
1. Printing the FAT16 image specs from BPB
2. Calling the function to get the root directory
3. Try to read the content of the root directory, if there is any
4. Recover file cluster chains, givent that the root directory is empty
5. Recover the chains metadata, verifying if a specific chain of clusters is a direcotry, then retrieve files data
6. Save the files (skipping the directories as plain files) from raw bytes to specific file formats, 
   based on their name and extentions contained in the metadata dictionary
"""

print(fat)
root_dir = fat.get_root_dir()
read_root_content()
check_fat_differences()

recovered_chains = create_chains().values()
metadata = decode_recovered_chains(recovered_chains)
save_files_from_chains(recovered_chains, metadata)
fat.close()