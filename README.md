# augmented_baker
Technical test for AI Sisters

Ideation:
- Affichage tool calls complet 
- Logs les discussions pour faire du debug
- Tool calls secure
- Madeleine n'est pas tech, on va pas lui mettre une interface dans le terminal. un petit front avec le Vercel AI sdk c'est pas mal
- Matcher la manière de parler de Madeleine avec un vocabulaire imagé
- Elle veut un assistant interne qui l'aide à gérer son business
- Langchain DeepAgents ? Langchain simple ? Langgraph overkill ?
- Rester pragmatique, le multi agents, usecase trop simple pour s'en servir
- Attention au fait de donner à l'agent de quoi executer des requêtes en DB
- confirmation l'envoie de mail
- Pour l'envoi de mails, mettre Madeleine en copie
- Tool libre idées:
    - A chaque début de conv, lancer un agents qui check les stocks
    - ...
- Description de la mission mentionne FastAPI, let's go sur ca 
- logging local langsmith ? file system 
- Utilisation de la nouvelle primitive SSE de fastAPI (release y a ~1,5 mois )


Pour un poste Senior :
- Utiliser le JS vs le python (vercel AI SDK vs une API first)
- pour un poste de senior, les questions que j’aurais posés sont :
- API model provider vs utiliser un model open source 
- Gros model vs petit model