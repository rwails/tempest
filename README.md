# Tempest #

This repository contains some of the code and data used to generate the
analyses found in

**Tempest: Temporal Dynamics in Anonymity Systems**  
Ryan Wails, Yixin Sun, Aaron Johnson, Mung Chiang, Prateek Mittal  
Proceedings on Privacy Enhancing Technologies, 2018  
<https://arxiv.org/abs/1801.01932>

Please contact `ryan DOT wails AT nrl DOT navy DOT mil` with questions.

## Usage ##

### Supported Platforms ###

Linux and Mac OSX are supported.

### Prerequisites ###

To build this code, you will need to first install

+ [CMake, minimum version 3.0.0](https://cmake.org/)
+ [GNU Make](https://www.gnu.org/software/make/)
+ A C++11-capable compiler, e.g. [g++](https://gcc.gnu.org/)
+ [The GNU Multiple Precision Arithmetic Library](https://gmplib.org/)
+ [Intel® TBB Library](https://www.threadingbuildingblocks.org/)
+ [Python3](https://www.python.org/)
+ [virtualenv](https://virtualenv.pypa.io/en/stable/)

### Building ###

The recommended installation steps are

1. Build the necessary executables and libraries
```bash
mkdir build
mkdir install
cd build
cmake -DCMAKE_INSTALL_PREFIX=../install ..
make && make install
```

2. Setup and source a Python virtualenv
```bash
virtualenv -p python3 env
source env/bin/activate
```

3. Install Python packages
```bash
git submodule init && git submodule update
cd pytricia && python3 setup.py build && python3 setup.py install && cd ..
```

## Acknowledgements ##

This work was supported by the Office of Naval Research (ONR) and by the
National Science Foundation (NSF) under grant numbers CNS-1527401, CNS-1423139
and CNS-1704105.  The views expressed in this work are strictly those of the
authors and do not necessarily reflect the official policy or position of ONR
or NSF.
