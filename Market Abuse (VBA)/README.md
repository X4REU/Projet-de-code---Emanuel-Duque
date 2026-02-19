---A SAVOIR---

Cette section présente l'utilité des différents dossiers présents dans le package.

Dans le dossier data, vous retrouverez l'ensemble des "API" que vous avez importées depuis le bouton "Data" du fichier Excel. 

Dans le dossier "symbol_list_avapi" vous retrouverez deux fichiers : 
-config.xlsx, qui recense le nombre d'API importés, dans une limite de 25 par jour,
-symbol_list.csv, qui sert de base de données afin de lister les API importables. 

Dans le dossier "reporting", vous retrouverez deux sous-dossiers : 
-"data_output"
-"reporting_1_doc_package"

Ces deux fichiers sont liés aux fonctions du bouton "Analyzer" du fichier Excel. 

Dans le dossier "data_output",vous retrouverez le détail des datas qui ont servi à mener l'analyse des transactions du client. 
Dans le dossier "reporting_1_doc_package", vous retrouverez le formulaire de déclaration d'opérations suspectes, complété et prêt à être envoyé. 

---Admin Info---

Pour accéder au fichier sans avoir à créer de User, vous pouvez utiliser l'identifiant suivant : 

Mail : admin
Password : admin
workbook password : admin (pour afficher le ruban)

---Scénarios---

Cette séction tend à présenter les différents indicateurs utilisé dans le logiciel. 
Les seuils sont variables et peuvent être fixés par l'utilisateur, le tout en fonction de la catégorisation du client : Retail ou Institutionnel.

🏢 Scénarios d’Alerte – Clients Institutionnels et Clients Retail :

1. Accumulation de volume → Détection de volumes anormalement élevés

✅ Transactions journalières dépassant un seuil prédéfini, exprimé en pourcentage du volumes quotidiens. 

✅ Achats cumulés sur X jours excédant un seuil défini, basé sur les volumes échangés sur la même période. 
2. Plus-value importante → Détection de gains potentiellement suspects

✅ Transaction générant une performance journalière supérieure à la volatilité constatée sur les X jours suivants,
ajustée selon la nature de l'opération (achat ou vente).
