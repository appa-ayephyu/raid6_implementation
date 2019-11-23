# Instructions to run the code
   ### Conda installation
   Linux:
   
   ```curl -o ~/miniconda.sh -O https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh``` 
   
   OSX:
   
   ```curl -o ~/miniconda.sh -O https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh``` 
   ```chmod +x ~/miniconda.sh
   ./miniconda.sh
   source ~/.bashrc
   ```
   
   Windows:
   
   ```Install https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe``` 

   ### Clone GitHub repo
   
   ```git clone https://github.com/appa-ayephyu/raid6_implementation.git
   cd raid6_implementation
   ```
   
   ### Install python libraries
   
   ```conda env create -f environment.yml
   source activate RAID6_Delivery
   ```
   
   ### Run the notebooks
   
   ```jupyter notebook```
   
   Run the test_raid6.ipynb file to test the implementation.
   
# RAID 6 Implementation
This implementation have been tested with Python 3.7.2

Initialize RAID6 with default parameters (can be changed in \_\_init__):
```python
import controller

RAID6 = controller.RAID6()
```

Write data from user input:
```python
RAID6.write_data("Data to store on RAID6", "name_of_the_data")
```

Write data to be stored as the new data in RAID6 system from file:
```python
RAID6.write_data_from_file("file to input", "new_file_name_on_RAID6_system")
eg. RAID6.write_data_from_file("input_picture.jpg", "picture"):
```

Update data to stored data in RAID6 system from file:
```python
RAID6.update_data_from_file("file to input as update data", "file_name_on_RAID6_system")
e.g. RAID6.update_data_from_file("update_picture.jpg", "picture")
```

Print data to file:
```python
RAID6.print_data_to_file("output file name","file_name_on_RAID6_system")
e.g. RAID6.print_data_to_file("picture_out.jpg","picture")
```

Recovery of disk corruption
do one disk corruption or 2 disks corruption
```
import shutil
shutil.rmtree('disks/disk_' + str(random_selected_disks[0]))
shutil.rmtree('disks/disk_' + str(random_selected_disks[1]))

### Print data to file

RAID6.print_data_to_file("output file name","file_name_on_RAID6_system")
The system should detect the disk corruption, execute recovery process and output the correct output file.
```

## Demo File
```
The step by step testing on Write, Read, Update, 1 disk corruption, 2 disk corruption, 
changing the number of disks for larger set of configuration, changing chunk size are 
presented in test_raid6.ipynb file.
```
