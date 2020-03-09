import pandas as pd
import numpy as np
import os

import pdftotext
from itertools import chain

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import stopwords
nltk.download('averaged_perceptron_tagger')

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation as LDA


def is_FactSet(filepath):
    check_words = ["Corrected Transcript",
                  "www.callstreet.com",
                  "FactSet CallStreet, LLC"]
    pdfFileObj = open(filepath,'rb')
    pdf = pdftotext.PDF(pdfFileObj)
    text = "\n\n".join(pdf)
    if all([ check_word in text for check_word in check_words]):
        return("FactSet")
    else:
        return("plain")
    


def get_fp_cp(fp):
    # fp means front page: from first page to Corporate Participants
    # get names of Corporate Participants
    output = list()
    for item in fp[fp.index("CORPORATE PARTICIPANTS"):]:
        if "Walmart" in item:
            for x in item.split("."):
                output = output + x.split(",")
            for x in item.split("-"):
                output = output + x.split("   ")
            for x in item.split("-"):
                output = output + x.split(".")
            for x in item.split("   "):
                output = output + x.split(",")
        else: 
            output = output + item.split()
    return([item.strip() for item in output if len(item) > 1]) 



def parse_FactSet_para(filepath, filename):
    """ return a dataframe, each row is a paragraph spoken by one person
    """ 
    pdfFileObj = open(filepath,'rb')
    pdf = pdftotext.PDF(pdfFileObj)
    text = "\n\n".join(pdf)

    tmp = text.split("........................................\
..............................................................\
..............................................................\
..................................................................................")

    # process words appeared in the front page and CORPORATE PARTICIPANTS section
    # fp means front page: from first page to Corporate Participants
    # fp contains a lot of info that repeat in the file
    fp = [item.strip() for item in tmp[0].split("\r\n") if len(item)>=1]

    # 
    to_be_removed = [fp[0], fp[1], fp[3]] + \
                    fp[2].split() + \
                    [x for x in fp[5].split(" ") if len(x) >= 1]

    # sort words to be removed by len to prevent missing to remove longer words
    to_be_removed_df = pd.DataFrame(set(to_be_removed))
    to_be_removed_df["len"] = to_be_removed_df[0].map(lambda x: len(x))
    to_be_removed_df = to_be_removed_df.sort_values(["len"], ascending = False)

    # remove words from fp
    for item in to_be_removed_df[0]:
        for i in range(1, len(tmp)):
            tmp[i] = tmp[i].replace(item, '')

    # remove "\r\n"
    for i in range(1, len(tmp)):
        tmp[i] = tmp[i].replace("\r\n", ' ').lstrip(", ")

    # 
    tmp = pd.DataFrame(tmp[2:], columns=["paragraph"])
    
    # add date
    tmp["date"] = pd.to_datetime(filename[:8])

    return(tmp)



def filenames_to_para(path, filenames):
    paragraphs = pd.DataFrame()
    for filename in filenames:
        filepath = path + "\\" + filename
        paragraphs = pd.concat([paragraphs, parse_FactSet_para(filepath, filename)], ignore_index=True)
    return(paragraphs)



def get_unique_words(para_tokens):
    all_tokens = list(chain.from_iterable(para_tokens))
    all_tokens = pd.Series(all_tokens)
    tokens_count = all_tokens.value_counts()
    return(tokens_count)

    

# collect all tagged tokens
def get_all_wordsPos(token_pos, duplicate=False):
    all_tokens = pd.Series(chain.from_iterable(token_pos))
    if duplicate == True:
        all_tokens = all_tokens.drop_duplicates()
    d = {"word": all_tokens.map(lambda x: x[0]),
         "pos": all_tokens.map(lambda x: x[1])}
    return(pd.DataFrame(d))



# this is for wordnet lemmatizer to recognize POS
def get_wordnet_pos(treebank_tag):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return ''



# Helper function
def print_topics(model, count_vectorizer, n_top_words):
    words = count_vectorizer.get_feature_names()
    for topic_idx, topic in enumerate(model.components_):
        print("\nTopic #%d:" % topic_idx)
        print(" ".join([words[i]
                        for i in topic.argsort()[:-n_top_words - 1:-1]]))
