# korean digit recognition
import numpy as np
import matplotlib.pyplot as plt
#from scikits.talkbox.features import mfcc
#librosa.feature.mfcc(*, y=None, sr=22050, S=None, n_mfcc=20, dct_type=2, norm='ortho', lifter=0, **kwargs)[source]
from librosa.feature import mfcc
from scipy.io import wavfile
from hmmlearn import hmm
import numpy as np
import os
import warnings
import scipy.stats as sp
import sys


warnings.filterwarnings("ignore")

fpaths = []
labels = []
spoken = []
features = []

# find files
apath = 'segmented'
for f in os.listdir(apath):
    apath2 = apath + '/' + f
    for w in os.listdir(apath2):
        file = apath2 + '/' + w
        print(file)
        fpaths.append(file)
        labels.append(f)
        if f not in spoken:
            spoken.append(f)
print('Words spoken:', spoken)

# extract MFCC features
#num_mfcc = 6
#num_mfcc = 10
num_mfcc = int(sys.argv[1])
for n, file in enumerate(fpaths):
    samplerate, d = wavfile.read(file)
    #features.append(mfcc(d, nwin=int(samplerate * 0.03), fs=samplerate, nceps= 6)[0])
    x = np.float32(d)
    hop=samplerate//100
    mc = mfcc(y=x, sr=samplerate, n_mfcc=num_mfcc, hop_length=hop, win_length=hop*2)
    features.append(np.transpose(mc, (1,0)))
    
print(len(features))
print(features[0].shape)


# shuffling the data
c = list(zip(features, labels))
np.random.shuffle(c)
features,labels = zip(*c)

print(len(features))
print(len(labels))

# test and training for 100 
nfiles = len(labels)
ntest = nfiles // 5    # last one of the 5-fold 
ntrain = nfiles - ntest 

m_trainingsetfeatures = features[0:ntrain]
m_trainingsetlabels = labels[0:ntrain]

print(len(m_trainingsetfeatures))
print(len(m_trainingsetlabels))

m_testingsetfeatures = features[ntrain:]
m_testingsetlabels = labels[ntrain:]


print(len(m_testingsetfeatures))
print(len(m_testingsetlabels))


gmmhmmindexdict = {}
index = 0
for word in spoken:
    gmmhmmindexdict[word] = index
    index = index +1


print ('Loading data completed')

#Parameters needed to train GMMHMM
m_num_of_HMMStates = 3  # number of states
#m_num_of_HMMStates = 6  # number of states
m_num_of_mixtures = 2  # number of mixtures for each hidden state
m_covarianceType = 'diag'  # covariance type
m_n_iter = 10  # number of iterations
m_bakisLevel = 2


def initByBakis(inumstates, ibakisLevel):
    startprobPrior = np.zeros(inumstates)
    startprobPrior[0: ibakisLevel - 1] = 1/float((ibakisLevel - 1))
    transmatPrior = getTransmatPrior(inumstates, ibakisLevel)
    return startprobPrior, transmatPrior


def getTransmatPrior(inumstates, ibakisLevel):
    transmatPrior = (1 / float(ibakisLevel)) * np.eye(inumstates)

    for i in range(inumstates - (ibakisLevel - 1)):
        for j in range(ibakisLevel - 1):
            transmatPrior[i, i + j + 1] = 1. / ibakisLevel

    for i in range(inumstates - ibakisLevel + 1, inumstates):
        for j in range(inumstates - i - j):
            transmatPrior[i, i + j] = 1. / (inumstates - i)

    return transmatPrior

m_startprobPrior ,m_transmatPrior = initByBakis(m_num_of_HMMStates,m_bakisLevel)


print("StartProbPrior=")
print(m_startprobPrior)

print("TransMatPrior=")
print(m_transmatPrior)


class SpeechModel:
    def __init__(self,Class,label):
        self.traindata = np.zeros((0,num_mfcc))
        self.Class = Class
        self.label = label
        self.model  = hmm.GMMHMM(n_components = m_num_of_HMMStates, n_mix = m_num_of_mixtures, \
                           transmat_prior = m_transmatPrior, startprob_prior = m_startprobPrior, \
                                        covariance_type = m_covarianceType, n_iter = m_n_iter)



# GMMHMM Models 
speechmodels = [None] * len(spoken)


for key in gmmhmmindexdict:
    speechmodels[gmmhmmindexdict[key]] = SpeechModel(gmmhmmindexdict[key],key)

for i in range(0,len(m_trainingsetfeatures)):
     for j in range(0,len(speechmodels)):
         if int(speechmodels[j].Class) == int(gmmhmmindexdict[m_trainingsetlabels[i]]):
            speechmodels[j].traindata = np.concatenate((speechmodels[j].traindata , m_trainingsetfeatures[i]))



for speechmodel in speechmodels:
    speechmodel.model.fit(speechmodel.traindata)


print ('Training completed -- {0} GMM-HMM models are built for {0} different types of words'.format(len(spoken)))
print (" ")
print(" ")

print("Prediction started")



#Testing
m_PredictionlabelList = []

for i in range(0,len(m_testingsetfeatures)):
    scores = []
    for speechmodel in speechmodels:
         scores.append(speechmodel.model.score(m_testingsetfeatures[i]))
    id  = scores.index(max(scores))
    m_PredictionlabelList.append(speechmodels[id].Class)
    print(str(np.round(scores, 3)) + " " + str(max(np.round(scores, 3))) +" "+":"+ speechmodels[id].label)

accuracy = 0.0
count = 0


print("")
print("Prediction for Testing DataSet:")

for i in range(0,len(m_testingsetlabels)):
    print( "Label"+str(i+1)+":"+m_testingsetlabels[i])
    if gmmhmmindexdict[m_testingsetlabels[i]] == m_PredictionlabelList[i]:
       count = count+1

accuracy = 100.0*count/float(len(m_testingsetlabels))

print("")
print("accuracy ="+str(accuracy))
print("")





#Calcuation of  mean ,entropy and relative entropy parameters
'''Entropyvalues for the 3 hidden states and 100 samples'''

def EntropyCalculator(dataarray,meanvalues,sigmavalues):
    entropyvals = []
    for i in range(0,len(dataarray[0])):
        totallogpdf = 0
        entropy = 0
        for j in range(0,len(dataarray)):
            totallogpdf += sp.norm.logpdf(dataarray[j,i],meanvalues[i],sigmavalues[i])
            entropy = (-1*totallogpdf)/len(dataarray)
        entropyvals.append(entropy)
    return entropyvals

'''Relative Entropyvalues for the 6 columns of the given data and sampled values'''
def RelativeEntropyCalculator(givendata,samplesdata,givendatasigmavals,sampledsigmavals,givendatameanvals,sampledmeanvals):

    absgivendatasigmavals =  [abs(number) for number in givendatasigmavals]
    abssampleddatasigmavals = [abs(number) for number in sampledsigmavals]
    relativeentropyvals = []

    for i in range(0,len(givendata[0])):
        totallogpdf = 0
        relativeentropy = 0
        for j in range(0,len(givendata)):
            totallogpdf +=(sp.norm.logpdf(samplesdata[j,i],sampledmeanvals[i],abssampleddatasigmavals[i])- sp.norm.logpdf(givendata[j,i],givendatameanvals[i],absgivendatasigmavals[i]))
            relativeentropy = (-1*totallogpdf)/float(len(givendata))
        relativeentropyvals.append(relativeentropy)
    return relativeentropyvals

cnt = 0

#for speechmodel in speechmodels:
if False:
    print("For GMMHMM with label:" +speechmodel.label)
    samplesdata,state_sequence = speechmodel.model.sample(n_samples=len(speechmodel.traindata))

    sigmavals =[]
    meanvals  =[]

    for i in range(0, len(speechmodel.traindata[0])):
        sigmavals.append(np.mean(speechmodel.traindata[:, i]))
        meanvals.append(np.std(speechmodel.traindata[:, i]))


    sampledmeanvals = []
    sampledsigmavals =[]



    for i in range(0,len(samplesdata[0])):
        sampledmeanvals.append(np.mean(samplesdata[:,i]))
        sampledsigmavals.append(np.std(samplesdata[:,i]))




    GivenDataEntropyVals = EntropyCalculator(speechmodel.traindata,meanvals,meanvals)
    SampledValuesEntropyVals = EntropyCalculator(samplesdata,sampledmeanvals,sampledsigmavals)
    RelativeEntropy = RelativeEntropyCalculator(speechmodel.traindata,samplesdata,sigmavals,sampledsigmavals,meanvals,sampledmeanvals)

    print("MeanforGivenDataValues:")
    roundedmeanvals = np.round(meanvals, 3)
    print(str(roundedmeanvals))
    print("")

    print("EntropyforGivenDataValues:")
    roundedentropyvals = np.round(GivenDataEntropyVals, 3)
    print(str(roundedentropyvals))
    print("")

    print("MeanforSampleddatavalues:")
    roundedsampledmeanvals = np.round(sampledmeanvals, 3)
    print(str(roundedsampledmeanvals))
    print("")

    print("EntropyforSampledDataValues:")
    roundedsampledentvals = np.round(SampledValuesEntropyVals, 3)
    print(str(roundedsampledentvals))
    print("")

    print("RelativeEntopyValues:")
    roundedrelativeentvals = np.round(RelativeEntropy, 3)
    print(str(roundedrelativeentvals))
    print("")







