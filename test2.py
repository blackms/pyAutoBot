import tensorflow as tf
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.layers import LSTM, Embedding, Dense, Input, Bidirectional, TimeDistributed

# Preparazione dei dati (questo è solo un esempio e potrebbe richiedere ulteriori passaggi)
words = list(set([word for sentence in sentences for word in sentence]))
tags = ["O", "B-EMAIL", "I-EMAIL", "B-PHONE", "I-PHONE"]  # ecc.
word2idx = {w: i for i, w in enumerate(words)}
tag2idx = {t: i for i, t in enumerate(tags)}
idx2tag = {i: t for t, i in tag2idx.items()}

X_data = [[word2idx[w] for w in s] for s in sentences]
Y_data = [[tag2idx[t] for t in ts] for ts in tag_sequences]

# Creazione del modello
input = Input(shape=(None,))
model = Embedding(input_dim=len(words), output_dim=50, input_length=140)(input)
model = Dropout(0.1)(model)
model = Bidirectional(LSTM(units=100, return_sequences=True, recurrent_dropout=0.1))(model)
model = TimeDistributed(Dense(len(tags), activation="softmax"))(model)
model = tf.keras.Model(input, model)

model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])

# Addestramento
model.fit(X_data, Y_data, batch_size=32, epochs=5, validation_split=0.1, verbose=1)
