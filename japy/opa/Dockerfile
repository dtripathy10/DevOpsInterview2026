FROM node:18-alpine

WORKDIR /sample-node-app

COPY index.js /sample-node-app/
COPY package.json /sample-node-app/

RUN npm install

EXPOSE 80

CMD ["node", "index"]