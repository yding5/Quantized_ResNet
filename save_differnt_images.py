import argparse
import os
import time
import shutil

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.backends.cudnn as cudnn
from torch.autograd import Variable
from myoptimizer.sgd_customized import SGD_CUSTOMIZED
from myoptimizer.sgd_threshold_pact import SGD_THRESHOLD_PACT
import torchvision
import torchvision.transforms as transforms
import copy
# from models import *
from models.resnet_cifar_pact import *
import numpy as np

parser = argparse.ArgumentParser(description='PyTorch Cifar10 Training')
parser.add_argument('--act', help='act type', action='store',default='BinAct')
parser.add_argument('--epochs', default=200, type=int, metavar='N', help='number of total epochs to run')
parser.add_argument('--start_epoch', default=0, type=int, metavar='N', help='manual epoch number (useful on restarts)')
parser.add_argument('-b', '--batch-size', default=128, type=int, metavar='N', help='mini-batch size (default: 128),only used for train')
parser.add_argument('--lr', '--learning-rate', default=0.1, type=float, metavar='LR', help='initial learning rate')
parser.add_argument('--momentum', default=0.9, type=float, metavar='M', help='momentum')
parser.add_argument('--weight_decay', '--wd', default=0, type=float, metavar='W', help='weight decay (default: 1e-4)')
parser.add_argument('--print_freq', '-p', default=10, type=int, metavar='N', help='print frequency (default: 10)')
parser.add_argument('--resume', default='', type=str, metavar='PATH', help='path to latest checkpoint (default: none)')
parser.add_argument('-e', '--evaluate', dest='evaluate', action='store_true', help='evaluate model on validation set')
parser.add_argument('-ct', '--cifar-type', default='10', type=int, metavar='CT', help='10 for cifar10,100 for cifar100 (default: 10)')
parser.add_argument('--log_file', help='log file', action='store',default='log_0614_CIFAR10.txt')
parser.add_argument('--significant_bit', help='bits to represent discrete num', action='store', type=int,
                    default=2)
parser.add_argument('--bit_threshold', help='bit to define 0', action='store', type=int,
                    default=20)
parser.add_argument('--quantize_layer1', help='quantization of layer1 input', action='store', type=int,
                    default=8)
parser.add_argument('--quantize_layer2', help='quantization of layer2 input', action='store', type=int,
                    default=8)
parser.add_argument('--quantize_layer3', help='quantization of layer3 input', action='store', type=int,
                    default=8)
parser.add_argument('--use_quantize_weight', help='weight quantization', action='store_true', default=False)
parser.add_argument('--sigmoid_alpha', help='scaling of sigmoid', action='store', type=float,
                    default=100)
parser.add_argument('--loss_regu', help='relaxation parameter laied on loss reglaization', action='store', type=float,
                    default=0.01)
parser.add_argument('--weight_thres', help='a weight threshold parameter using memorization', action='store', type=float,
                    default=0.1)
parser.add_argument('--use_alpha_decay', help='enable alpha decay in sigmoid gradient', default=False, action='store_true')
#parser.add_argument('--use_quadratic_decay', help='enable quadratic alpha decay instead of linear decay', default=False, action='store_true')
parser.add_argument('--start_alpha', help='starting scaling of sigmoid', action='store', type=float, default=100)
parser.add_argument('--end_alpha', help='ending scaling of sigmoid', action='store', type=float, default=100)
parser.add_argument('--alpha_decay_type', default='1', type=int, help='type of alpha decay strategy')
parser.add_argument('--lr_type', default='1', type=int, help='type of lr decay strategy')
parser.add_argument('--save_output', help='save raw output of best', action='store_true', default=False)
parser.add_argument('--filename', default='', type=str, metavar='PATH', help='name to save raw ouput (default: none)')

args = parser.parse_args()

best_prec = 0

print('epochs: ', args.epochs)
print('learning rate: ', args.lr)
print('momentum: ', args.momentum)
print('print-freq: ', args.print_freq)
print('log file: ', args.log_file)
print("bit_threshold: ", args.bit_threshold)
print("significant_bit: ", args.significant_bit)
print("quantize_layer1: ", args.quantize_layer1)
print("quantize_layer2: ", args.quantize_layer2)
print("quantize_layer3: ", args.quantize_layer3)
print("solver quantization: ", args.use_quantize_weight)
print("sigmoid_alpha: ", args.sigmoid_alpha)
print("loss_regu: ", args.loss_regu)
print("weight_thres: ", args.weight_thres)
print("use_alpha_decay: ", args.use_alpha_decay)
print("start_alpha: ",args.start_alpha)
print("end_alphaL: ", args.end_alpha)
print("Quantization Type:", args.act)
print("alpha decay Type:", args.alpha_decay_type)
print("lr decay Type:", args.lr_type)
print("batch_size:", args.batch_size)
print("batch_size:", args.filename)


with open(args.log_file,'a') as log:
    print('CIRAR10 baseline using resnet20',file=log)
    print('epochs: ', args.epochs, file=log)
    print('learning rate: ', args.lr, file=log)
    print('momentum: ', args.momentum, file=log)
    print('print-freq: ', args.print_freq, file=log)
    print('log file: ', args.log_file, file=log)
    print("bit_threshold: ", args.bit_threshold, file=log)
    print("significant_bit: ", args.significant_bit, file=log)
    print("quantize_layer1: ", args.quantize_layer1, file=log)
    print("quantize_layer2: ", args.quantize_layer2, file=log)
    print("quantize_layer3: ", args.quantize_layer3, file=log)
    print("solver quantization: ", args.use_quantize_weight, file=log)
    print("sigmoid_alpha: ", args.sigmoid_alpha, file=log)
    print("loss_regu: ", args.loss_regu, file=log)
    print("weight_thres: ", args.weight_thres, file=log)
    print("use_alpha_decay: ", args.use_alpha_decay, file=log)
    print("start_alpha: ",args.start_alpha, file=log)
    print("end_alphaL: ", args.end_alpha, file=log)
    print("Quantization Type:", args.act, file=log)
    print("batch_size:", args.batch_size, file=log)
    print("alpha decay Type:", args.alpha_decay_type, file=log)
    print("lr decay Type:", args.lr_type, file=log)
    print("filename:", args.filename, file=log)


def getname(model):
    name_list = []
    """
    with open('debug_0731.txt','a') as log:
        print(model,file=log)
        print('',file=log)
        print('',file=log)
        print('',file=log)
    """
    for name,submodel in model.named_children():
        sublist = getname(submodel)
        if len(sublist) is 0:
            name_list.append(name)
        else:
            name_list.extend(sublist)

    return name_list


def main():
    global args, best_prec
    args = parser.parse_args()
    use_gpu = torch.cuda.is_available()
    torch.set_printoptions(precision=10)
    if args.act == 'BinAct':
        myBlock = BasicBlock_BinAct
    elif args.act == 'PlainBinAct':
        myBlock = PlainBlock_BinAct
    elif args.act == 'FP':
        myBlock = BasicBlock_FP
    elif args.act == 'sig':
        myBlock = BasicBlock_BinAct_sig
    elif args.act == 'Plainsig':
        myBlock = PlainBlock_BinAct_sig
    elif args.act == 'pact':
        myBlock = BasicBlock_BinAct_pact
    elif args.act == 'pact_sig':
        myBlock = BasicBlock_BinAct_pact_sigmoid
    elif args.act == 'pact_sig_lr0':
        myBlock = BasicBlock_BinAct_pact_sigmoid_lr0
    else:
        print('unknow act type')
        return 1
 
    # Model building
    print('=> Building model...')
    if use_gpu:
        # model can be set to anyone that I have defined in models folder
        # note the model should match to the cifar type !
        model = ResNet_Cifar(myBlock,
                             [3, 3, 3], 
                             [args.quantize_layer1, args.quantize_layer2, args.quantize_layer3],
                             alpha=args.sigmoid_alpha,
                             loss_regu=args.loss_regu,
                            )
        
        # model = resnet20_cifar()
        # model = resnet32_cifar()
        # model = resnet44_cifar()
        # model = resnet110_cifar()
        # model = preact_resnet110_cifar()
        # model = resnet164_cifar(num_classes=100)
        # model = resnet1001_cifar(num_classes=100)
        # model = preact_resnet164_cifar(num_classes=100)
        # model = preact_resnet1001_cifar(num_classes=100)

        # model = wide_resnet_cifar(depth=26, width=10, num_classes=100)

        # model = resneXt_cifar(depth=29, cardinality=16, baseWidth=64, num_classes=100)
        
        # model = densenet_BC_cifar(depth=190, k=40, num_classes=100)

        print(model)
        model.weight_thres = 0
        weight_thres = args.weight_thres
        name_list = getname(model)
        print(name_list)
        print(len(name_list))
        param_list = []
        for name in name_list:
            if name=='0':
                param_list.append('conv')
            elif name=='1':
                param_list.append('bn')
                param_list.append('bn')
            elif name[0:2]=='bn':
                param_list.append(name)
                param_list.append(name)
            elif name[0:4]=='conv':
                param_list.append(name)
            elif name[0:2]=='fc':
                param_list.append(name)
                param_list.append(name)
        # print(param_list)
        # print(len(param_list))


        # mkdir a new folder to store the checkpoint and best model
        if not os.path.exists('result'):
            os.makedirs('result')
        fdir = 'result/resnet20_cifar10'
        if not os.path.exists(fdir):
            os.makedirs(fdir)



        # adjust the lr according to the model type
        """
        if isinstance(model, (ResNet_Cifar, PreAct_ResNet_Cifar)):
            model_type = 1
        elif isinstance(model, Wide_ResNet_Cifar):
            model_type = 2
        elif isinstance(model, (ResNeXt_Cifar, DenseNet_Cifar)):
            model_type = 3
        else:
            print('model type unrecognized...')
            return
        """
        #model_type = args.lr_type
        model = nn.DataParallel(model).cuda()
        criterion = nn.CrossEntropyLoss().cuda()
        if args.use_quantize_weight==False:
            # optimizer using full precision weight
            optimizer = SGD_CUSTOMIZED(model.parameters(), lr=args.lr, momentum=args.momentum, weight_decay=args.weight_decay)
        else:
            # optimizer using quantized bit with weight thresholding
            optimizer = SGD_THRESHOLD_PACT(model.parameters(), lr = args.lr, momentum=args.momentum, weight_decay=args.weight_decay,param_list=param_list)
        cudnn.benchmark = True
    else:
        print('Cuda is not available!')
        return

    if args.resume:
        if os.path.isfile(args.resume):
            print('=> loading checkpoint "{}"'.format(args.resume))
            checkpoint = torch.load(args.resume)
            args.start_epoch = checkpoint['epoch']
            best_prec = checkpoint['best_prec']
            model.load_state_dict(checkpoint['state_dict'])
            optimizer.load_state_dict(checkpoint['optimizer'])
            print("=> loaded checkpoint '{}' (epoch {})".format(args.resume, checkpoint['epoch']))
        else:
            print("=> no checkpoint found at '{}'".format(args.resume))

    # Data loading and preprocessing
    # CIFAR10
    if args.cifar_type == 10:
        print('=> loading cifar10 data...')
        normalize = transforms.Normalize(mean=[0.491, 0.482, 0.447], std=[0.247, 0.243, 0.262])

        train_dataset = torchvision.datasets.CIFAR10(
            root='./data/CIFAR10', 
            train=True, 
            download=True,
            transform=transforms.Compose([
                transforms.RandomCrop(32, padding=4),
                transforms.RandomHorizontalFlip(),
                transforms.ToTensor(),
                normalize,
            ]))
        trainloader = torch.utils.data.DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=2)

        test_dataset = torchvision.datasets.CIFAR10(
            root='./data/CIFAR10',
            train=False,
            download=True,
            transform=transforms.Compose([
                transforms.ToTensor(),
                
            ]))
        testloader = torch.utils.data.DataLoader(test_dataset, batch_size=100, shuffle=False, num_workers=2)
    # CIFAR100
    elif args.cifar_type == 100:
        print('=> loading cifar100 data...')
        normalize = transforms.Normalize(mean=[0.507, 0.487, 0.441], std=[0.267, 0.256, 0.276])

        train_dataset = torchvision.datasets.CIFAR100(
            root='./data',
            train=True,
            download=True,
            transform=transforms.Compose([
                transforms.RandomCrop(32, padding=4),
                transforms.RandomHorizontalFlip(),
                transforms.ToTensor(),
                normalize,
            ]))
        trainloader = torch.utils.data.DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=2)

        test_dataset = torchvision.datasets.CIFAR100(
            root='./data',
            train=False,
            download=True,
            transform=transforms.Compose([
                transforms.ToTensor(),
                normalize,
            ]))
        testloader = torch.utils.data.DataLoader(test_dataset, batch_size=100, shuffle=False, num_workers=2)
    elif args.cifar_type == 100:
        traindir = '~/raw-data/train'
        valdir = '~/raw-data/validation'
        normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

        train_dataset = datasets.ImageFolder(traindir,  transforms.Compose([ transforms.RandomResizedCrop(224),  transforms.RandomHorizontalFlip(), transforms.ToTensor(), normalize,  ]))

    #if args.distributed:
    #    train_sampler = torch.utils.data.distributed.DistributedSampler(train_dataset)
    #else:
        train_sampler = None

        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=args.batch_size, shuffle=(train_sampler is None), num_workers=2, pin_memory=True, sampler=train_sampler)

        val_loader = torch.utils.data.DataLoader( datasets.ImageFolder(valdir, transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            normlize,
             ])),
        batch_size=args.batch_size, shuffle=False,
        num_workers=2, pin_memory=True)
    else:
        print('unknown cifar type')
        return

    if args.evaluate:
        validate(testloader, model, criterion)
        return
    for epoch in range(args.start_epoch, args.epochs):
        adjust_learning_rate(optimizer, epoch, args.lr_type)
        # print(model.bn1.track_running_stats)

        # train for one epoch
        weight_thres = train(trainloader, model, criterion, optimizer, epoch, weight_thres)
        # print(model.bn1.track_running_stats)

        # generate a new model with parameters being quantized
        print('Testing on model of full precision')
        with open(args.log_file,'a') as log:
            print('Testing on model of full precision', file=log)
        
        # evaluate on test set
        prec, raw_output, target = validate(testloader, model, criterion)

        # remember best precision and save checkpoint
        is_best = prec > best_prec
        if ((epoch >= 170 and epoch <= 200) or epoch>=320) and args.save_output:
            np.save(args.filename+'_'+str(epoch)+'_raw_output', np.asarray(raw_output))
            np.save(args.filename+'_'+str(epoch)+'_val_target', np.asarray(target))
        best_prec = max(prec,best_prec)
        save_checkpoint({
            'epoch': epoch + 1,
            'state_dict': model.state_dict(),
            'best_prec': best_prec,
            'optimizer': optimizer.state_dict(),
        }, is_best, fdir)

class AverageMeter(object):
    """Computes and stores the average and current value"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def train(trainloader, model, criterion, optimizer, epoch, weight_thres):
    batch_time = AverageMeter()
    data_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()

    model.train()
    end = time.time()

    # TODO: automatically adjustify sigmoid factor for different network
    # scaled sigmoid argument increased as epochs, need to customized this function manually
    current_alpha = adjust_alpha(epoch, args.alpha_decay_type, args.start_alpha, args.end_alpha)
    if args.use_alpha_decay: 
        for item in model.module.layer1.modules():
            if isinstance(item, BasicBlock_BinAct_pact_sigmoid_lr0) or isinstance(item, BasicBlock_BinAct_pact_sigmoid) or isinstance(item, BasicBlock_BinAct) or isinstance(item, BasicBlock_BinAct_pact) or isinstance(item, BasicBlock_BinAct_sig):
                item.binact1.alpha = current_alpha
                item.binact2.alpha = current_alpha
        for item in model.module.layer2.modules():
            #if isinstance(item, BasicBlock):
            if isinstance(item, BasicBlock_BinAct_pact_sigmoid_lr0) or isinstance(item, BasicBlock_BinAct_pact_sigmoid) or isinstance(item, BasicBlock_BinAct) or isinstance(item, BasicBlock_BinAct_pact) or isinstance(item, BasicBlock_BinAct_sig):
                item.binact1.alpha = current_alpha
                item.binact2.alpha = current_alpha
        for item in model.module.layer3.modules():
            #if isinstance(item, BasicBlock):
            if isinstance(item, BasicBlock_BinAct_pact_sigmoid_lr0) or isinstance(item, BasicBlock_BinAct_pact_sigmoid) or isinstance(item, BasicBlock_BinAct) or isinstance(item, BasicBlock_BinAct_pact) or isinstance(item, BasicBlock_BinAct_sig):
                item.binact1.alpha = current_alpha
                item.binact2.alpha = current_alpha

    for i, (input, target) in enumerate(trainloader):
        # measure data loading time
        data_time.update(time.time() - end)
        input, target = input.cuda(), target.cuda()
        input_var = Variable(input)
        target_var = Variable(target)

        # compute output
        output = model(input_var)
        loss = criterion(output, target_var)
        
        # measure accuracy and record loss
        prec = accuracy(output.data, target)[0]
        losses.update(loss.data.item(), input.size(0))
        top1.update(prec.item(), input.size(0))

        # compute gradient and do SGD step
        optimizer.zero_grad()
        loss.backward()
        if args.use_quantize_weight:
            weight_thres = optimizer.step(weight_thres)
        else:
            optimizer.step()
        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

        if i % args.print_freq == 0 or i == len(trainloader)-1:
            print('Epoch: [{0}][{1}/{2}]\t'
                  'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Data {data_time.val:.3f} ({data_time.avg:.3f})\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  'Prec {top1.val:.3f}% ({top1.avg:.3f}%)'.format(
                   epoch, i, len(trainloader), batch_time=batch_time,
                   data_time=data_time, loss=losses, top1=top1))

            with open(args.log_file,'a') as log:
                print('Epoch: [{0}][{1}/{2}]\t'
                  'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Data {data_time.val:.3f} ({data_time.avg:.3f})\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  'Prec {top1.val:.3f}% ({top1.avg:.3f}%)'.format(
                   epoch, i, len(trainloader), batch_time=batch_time,
                   data_time=data_time, loss=losses, top1=top1),file=log)

    return weight_thres

def validate(val_loader, model, criterion):
    batch_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()

    # switch to evaluate mode
    model.eval()
 
    end = time.time()

    raw_output = []
    raw_target = []

    M0H1One = set(list(np.load('M0H1One.npy')))
    M0H1Three = set(list(np.load('M0H1Three.npy')))
    M0FH2One = set(list(np.load('M0FH2One.npy')))
    M0FH2Three = set(list(np.load('M0FH2Three.npy')))



    for i, (input, target) in enumerate(val_loader):

        for ii in range(100):
            ID = i*100 + ii
            if ID in M0H1One:
                np.save('M0H1One/'+str(ID),input[ii].numpy()) 
            if ID in M0H1Three:
                np.save('M0H1Three/'+str(ID),input[ii].numpy()) 
            if ID in M0FH2One:
                np.save('M0FH2One/'+str(ID),input[ii].numpy()) 
            if ID in M0FH2Three:
                np.save('M0FH2Three/'+str(ID),input[ii].numpy()) 


        input, target = input.cuda(), target.cuda()
        input_var = Variable(input)
        target_var = Variable(target)

        # compute output
        output = model(input_var)
        loss = criterion(output, target_var)
        raw_output.append(output.data.cpu().numpy())
        raw_target.append(target_var.data.cpu().numpy())
        
        # measure accuracy and record loss
        prec = accuracy(output.data, target)[0]
        losses.update(loss.data.item(), input.size(0))
        top1.update(prec.item(), input.size(0))

        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

        if i % args.print_freq == 0 or i == len(val_loader)-1:
            print('Test: [{0}/{1}]\t'
                  'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  'Prec {top1.val:.3f}% ({top1.avg:.3f}%)'.format(
                   i, len(val_loader), batch_time=batch_time, loss=losses,
                   top1=top1))

            with open(args.log_file,'a') as log:
                print('Test: [{0}/{1}]\t'
                  'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  'Prec {top1.val:.3f}% ({top1.avg:.3f}%)'.format(
                   i, len(val_loader), batch_time=batch_time, loss=losses,
                   top1=top1),file=log)



    print(' * Prec {top1.avg:.3f}% '.format(top1=top1))
    with open(args.log_file,'a') as log:
        print(' * Prec {top1.avg:.3f}% '.format(top1=top1),file=log)

    return top1.avg, np.asarray(raw_output), np.asarray(raw_target)


def save_checkpoint(state, is_best, fdir):
    filepath = os.path.join(fdir, 'checkpoint.pth')
    torch.save(state, filepath)
    if is_best:
        shutil.copyfile(filepath, os.path.join(fdir, 'model_best.pth.tar'))


def adjust_alpha(epoch, alpha_decay_type, start_alpha, end_alpha):
    if alpha_decay_type == 1:
        return args.start_alpha + epoch*(args.end_alpha-args.start_alpha)/args.epochs
    elif alpha_decay_type ==2:
        return args.start_alpha + (epoch/args.epochs)**2*(args.end_alpha-args.start_alpha)
    elif alpha_decay_type ==4:
        if epoch < 200:
            return 0.000001
        else:
            return args.start_alpha + ((epoch-200)/(args.epochs-200))**2*(args.end_alpha-args.start_alpha)
    elif alpha_decay_type ==5:
        if epoch > 100:
            return 0.000001
        else:
            return args.start_alpha + (epoch/100)*(args.end_alpha-args.start_alpha)
    elif alpha_decay_type ==6:
        if epoch < 200:
            return 0.0
        else:
            return args.start_alpha + ((epoch-200)/(args.epochs-200))**2*(args.end_alpha-args.start_alpha)
    else:
        print("unknown alpha type")
    return 0.0001 


def adjust_learning_rate(optimizer, epoch, lr_type):
    """For resnet, the lr starts from 0.1, and is divided by 10 at 80 and 120 epochs"""
    if lr_type == 1:
        """    
        if epoch < 80:
            lr = args.lr
        elif epoch < 120:
            lr = args.lr * 0.1
        else:
            lr = args.lr * 0.01
        """
        """
        if epoch<160:
            lr = 1-0.999*epoch*2/args.epochs
        else:
            lr = 0.001*(1-0.999*(epoch-160)*2/args.epochs)

        lr *= args.lr
        """
        
        if epoch < 60:
            lr = args.lr
        elif epoch < 120:
            lr = args.lr * 0.1
        elif epoch < 180:
            lr = args.lr * 0.01 
        else:
            lr = args.lr * 0.001
        

    elif lr_type == 2:
        if epoch < 60:
            lr = args.lr
        elif epoch < 120:
            lr = args.lr * 0.2
        elif epoch < 160:
            lr = args.lr * 0.04
        else:
            lr = args.lr * 0.008
    elif lr_type == 3:
        if epoch < 150:
            lr = args.lr
        elif epoch < 225:
            lr = args.lr * 0.1
        else:
            lr = args.lr * 0.01
    elif lr_type == 4:
        if epoch < 60:
            lr = args.lr
        elif epoch < 120:
            lr = args.lr * 0.1
        elif epoch < 180:
            lr = args.lr * 0.01 
        elif epoch < 200:
            lr = args.lr * 0.001
        elif epoch < 250:
            lr = args.lr * 0.1
        elif epoch < 300:
            lr = args.lr * 0.01
        else:
            lr = args.lr * 0.001
    elif lr_type == 5:
        if epoch < 60:
            lr = args.lr
        elif epoch < 120:
            lr = args.lr * 0.1
        elif epoch < 180:
            lr = args.lr * 0.01 
        elif epoch < 200:
            lr = args.lr * 0.001
        elif epoch < 250:
            lr = args.lr * 0.01
        else:
            lr = args.lr * 0.001
    elif lr_type == 6:
        if epoch < 60:
            lr = args.lr
        elif epoch < 120:
            lr = args.lr * 0.3
        elif epoch < 180:
            lr = args.lr * 0.03 
        elif epoch < 200:
            lr = args.lr * 0.003
        elif epoch < 250:
            lr = args.lr * 0.01
        else:
            lr = args.lr * 0.001
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr
    optimizer.lr = lr

def accuracy(output, target, topk=(1,)):
    """Computes the precision@k for the specified values of k"""
    maxk = max(topk)
    batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].view(-1).float().sum(0)
        res.append(correct_k.mul_(100.0 / batch_size))
    return res


if __name__=='__main__':
    main()

