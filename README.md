# 🏋️‍♂️ Fitness Coach AR

## 📝 Descrizione del Progetto
Fitness Coach AR è un'applicazione innovativa che utilizza la realtà aumentata e la computer vision per aiutarti durante i tuoi allenamenti. L'app monitora i tuoi movimenti in tempo reale attraverso la webcam, fornendo feedback immediati sulla corretta esecuzione degli esercizi e contando automaticamente le ripetizioni.

## ✨ Caratteristiche Principali
- 🎯 Rilevamento in tempo reale della postura
- 📊 Conteggio automatico delle ripetizioni
- 💬 Feedback immediato sulla forma
- 🔄 Supporto per diversi esercizi (Squat e Affondo)
- 👀 Interfaccia utente intuitiva

## 🛠 Requisiti di Sistema
- Python 3.10 o superiore
- Webcam funzionante
- Spazio sufficiente per i movimenti davanti alla webcam

## 📦 Dipendenze
- PyQt6: Per l'interfaccia grafica
- OpenCV (cv2): Per l'elaborazione video
- Mediapipe: Per il rilevamento della postura

## 🚀 Installazione
1. Clona il repository o scarica i file del progetto
2. Installa le dipendenze necessarie:
```bash
pip install -r requirements.txt
```

## 💻 Avvio dell'Applicazione
1. Naviga nella directory del progetto
2. Esegui il file principale:
```bash
python main.py
```

## 🎮 Guida all'Uso
1. **Avvio**: Lancia l'applicazione e concedi l'accesso alla webcam
2. **Selezione Esercizio**: Scegli tra Squat o Affondo dal menu a tendina
3. **Inizia l'Allenamento**: Clicca su "Inizia Allenamento"
4. **Esecuzione**:
   - Posizionati in modo che il tuo corpo sia completamente visibile
   - Segui il feedback in tempo reale per mantenere la forma corretta
   - Osserva il contatore delle ripetizioni
5. **Fine**: Clicca su "Termina Allenamento" quando hai finito

## 🎯 Esercizi Supportati

### Squat
- Mantieni la schiena dritta
- Piega le ginocchia come se dovessi sederti
- Scendi finché le cosce sono parallele al pavimento
- Risali mantenendo la postura corretta

### Affondo
- Parti in posizione eretta
- Fai un passo avanti piegando entrambe le ginocchia
- Il ginocchio posteriore deve quasi toccare il pavimento
- Risali e alterna le gambe

## 🔧 Struttura del Progetto
- `main.py`: File principale dell'applicazione
- `pose_detector.py`: Gestisce il rilevamento della postura
- `exercise_analyzer.py`: Analizza i movimenti e fornisce feedback
- `requirements.txt`: Lista delle dipendenze

## 🤝 Contribuire
Sei interessato a contribuire? Fantastico! Puoi:
- Segnalare bug
- Suggerire nuove funzionalità
- Aggiungere supporto per nuovi esercizi
- Migliorare la documentazione

## 📄 Licenza
Questo progetto è distribuito con licenza MIT. Sentiti libero di utilizzarlo, modificarlo e distribuirlo secondo le tue necessità.

---

*Fitness Coach AR - Il tuo allenatore personale in realtà aumentata* 🏋️‍♂️✨