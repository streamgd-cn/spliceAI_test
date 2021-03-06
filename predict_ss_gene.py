from utils import *

import numpy as np
from Bio import SeqIO

import tensorflow as tf

import plotly.offline as pyo
import plotly.graph_objs as go

# genome import, latest version
fasta_seq = SeqIO.parse(open('./data/chr21.fa'), 'fasta')

for fasta in fasta_seq:
    name, sequence = fasta.id, str(fasta.seq)

# file with all principal gene transcripts from GENCODE v33
transcript_file = np.genfromtxt('./data/GENCODE_v33_basic', usecols=(1, 3, 4, 5, 9, 10), dtype='str')

transcript_name = 'ENST00000612267' # AF254983.1

# flanking ends on each side are of this length to include some context
context = 1000

for row in transcript_file:
    # explicitly checking transcript_name
    if transcript_name in row[0]:
        # sequence from start to end
        s = sequence[int(row[2]) - context: int(row[3]) + context].upper()
        # adding the transcripts of the sense strand: whole transcript + flanks + zero-padded, labels + zero-padded
        if row[1] == '+':
            # extract the transcript sequence with 1k flanks
            if 'N' not in s:
                # padding labels here
                pad = 5000 - (len(s) - context * 2) % 5000
                es, ee = row[4].split(',')[:-1], row[5].split(',')[:-1]
                # decrease the pad length from both sides because the context-1 and context+sequence+1 sites are
                # donor and acceptor, respectively
                y = make_labels(s, context, es, ee)
                # padding sequence with Os
                s = (pad // 2) * 'O' + s + (pad - pad // 2) * 'O'
        # adding the transcripts of the antisense strand
        if row[1] == '-':
            if 'N' not in s:
                # padding labels here
                pad = 5000 - (len(s) - context * 2) % 5000
                # decrease the pad length from both sides because the context-1 and context+sequence+1 sites are
                # donor and acceptor, respectively
                es, ee = row[4].split(',')[:-1], row[5].split(',')[:-1]
                # decrease the pad length from both sides because the context-1 and context+sequence+1 sites are
				# donor and acceptor, respectively
                y = make_labels(s, context, es, ee)
                # hot-encoding labels and adding hot-encoded labels to a new list
                # getting complementary seq
                s = ''.join([complementary(x) for x in s])
                # padding sequence with Os
                s = (pad // 2) * 'O' + s + (pad - pad // 2) * 'O'
        break

# cut these sequences and labels into 5000 chunks
transcript_chunks = []
label_chunks = []

# transform into chunks 
chunks = (len(s) - context * 2) // 5000
for j in range(1, chunks + 1):
    transcript_chunks.append(s[5000 * (j - 1): 5000 * j + context * 2])
    label_chunks.append(y[5000 * (j - 1): 5000 * j])

# PREDICT -> y_pred

x_test, y_test = transform_input(transcript_chunks, label_chunks)

x_test = np.array(x_test)
y_test = np.array(y_test)

model = tf.keras.models.load_model('./data/model_spliceAI2k_chr1', compile=False)

y_pred = model.predict(x_test)

# Quantify

# Plot

es, ee = [int(i) - int(es[0]) for i in es], [int(i) - int(es[0]) for i in ee]

a, d = y_pred[:,:,1], y_pred[:,:,2]

a_, d_ = [], []
for row in a:
    a_.extend(row)
for row in d:
    d_.extend(row)

a_, d_ = a_[pad // 2 - 1:-pad // 2 + 1], d_[pad // 2 - 1:-pad // 2 + 1]

k = len(es)
a_topk_ind = np.argsort(a_, axis=-1)[-k:]
d_topk_ind = np.argsort(d_, axis=-1)[-k:]

print(len(a_topk_ind), len(d_topk_ind))

def add_exon_real(x_start, x_end):
    exon = go.Scatter(
        x=[x_start, x_end],
        y=[0.6, 0.6],
        mode='lines+markers',
        marker=dict(
            color='rgb(55, 255, 55)',
            size=6,
        ),
        line=dict(color='rgb(55, 255, 55)', width=2),
    )
    return exon


def add_exon_pred(x_start):
    exon = go.Scatter(
        x=[x_start],
        y=[0.5],
        mode='markers',
        marker=dict(
            color='rgb(255, 55, 55)',
            size=6,
        ),
    )
    return exon


data = []

for x in zip(es, ee):
    data.append(add_exon_real(x[0], x[1]))

for x in a_topk_ind:
    data.append(add_exon_pred(x))

for x in d_topk_ind:
    data.append(add_exon_pred(x))

layout = go.Layout(title='junctions AF254983.1')

fig = go.Figure(data=data, layout=layout)
fig['layout']['yaxis'].update(title='', range=[0.0, 1.0])
pyo.plot(fig, filename='junctions_lines.html')
