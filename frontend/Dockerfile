# build env
FROM node:21.7.1-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . ./
RUN npm run build
# Copy the contents of the build directory into the shared volume so nginx
# serves the React bundle from its web root.
CMD sh -c "cp -r build/. result_build"
