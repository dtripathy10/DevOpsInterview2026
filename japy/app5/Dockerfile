FROM node:18-alpine

WORKDIR /sample-node-app

COPY server.js /sample-node-app/
COPY package.json /sample-node-app/
COPY data.json /sample-node-app/

RUN npm install

EXPOSE 80

CMD ["node", "server"]