#!/bin/csh

#$ -M yding5@nd.edu	 # Email address for job notification
#$ -m abe		 # Send mail when job begins, ends and aborts
#$ -pe smp 2-4           # Specify parallel environment and legal core size
#$ -q gpu@qa-1080ti-001    # Specify queue (use ‘debug’ for development)
#$ -l gpu_card=1    # Specify number of GPU cards
#$ -N CS502_2       # Specify job name

module load python/3.6.0 torch    # Required modules
#source /opt/crc/c/caffe/1.0.0-rc5/1.0.0
#python mydebug.py
setenv CUDA_VISIBLE_DEVICES 3
python3.6 CIFAR_MAIN.py --lr 0.1 --epoch 350 --print_freq 200 --log_file logs/CS502_2.txt --quantize_layer1 2 --quantize_layer2 2 --quantize_layer3 2 --use_quantize_weight --loss_regu 0 --weight_thres 0.1 --act sig --save_output --filename 502_2 --lr_type 4 --alpha_decay_type 6 --use_alpha_decay --start_alpha 7.0 --end_alpha 7.0
