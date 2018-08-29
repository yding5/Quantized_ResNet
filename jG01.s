#!/bin/csh

#$ -M yding5@nd.edu	 # Email address for job notification
#$ -m abe		 # Send mail when job begins, ends and aborts
#$ -pe smp 2-4           # Specify parallel environment and legal core size
#$ -q gpu@qa-1080ti-005         # Specify queue (use ‘debug’ for development)
#$ -l gpu_card=1    # Specify number of GPU cards
#$ -N C50_1       # Specify job name

module load python/3.6.0 torch    # Required modules
#source /opt/crc/c/caffe/1.0.0-rc5/1.0.0
#python mydebug.py
setenv CUDA_VISIBLE_DEVICES 2
python3.6 CIFAR_BI_baseline.py --lr 0.1 --epoch 200 --print_freq 100 --log_file logs/C50_1.txt --quantize_layer1 2 --quantize_layer2 2 --quantize_layer3 2 --use_quantize_weight --loss_regu 0 --weight_thres 0.1 
