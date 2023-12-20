FROM gitpod/workspace-full:2023-05-08-21-16-55

# Some datasets work on 3.8 only
RUN pyenv install 3.8.15\
    && pyenv global 3.8.15

# VideoDataset
RUN sudo apt-get update && sudo apt-get install -y --no-install-recommends libgl1
RUN sudo apt-get install make
# https://stackoverflow.com/questions/69564238/puppeteer-error-failed-to-launch-the-browser-process
# https://github.com/puppeteer/puppeteer/blob/main/docs/troubleshooting.md#chrome-doesnt-launch-on-linux
RUN sudo apt-get install -y --no-install-recommends libatk-bridge2.0-0 libcups2 ca-certificates fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libgcc1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 lsb-release wget xdg-utils
