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
+ Python3

### Building ###

The recommended installation steps are

```bash
mkdir build
mkdir install
cd build
cmake -DCMAKE_INSTALL_PREFIX=../install ..
make && make install
```
