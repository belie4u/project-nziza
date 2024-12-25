#!/bin/bash
echo "Adding all changes..."
git add .

echo "Committing changes..."
git commit -m "new changes"

echo "Pushing to the repository..."
git push origin main


#!/bin/bash
echo "changing to main project"

cd shop

echo "changing to solr"

cd solr-6.6.6

echo "starting solr"

.\bin\solr.cmd start

echo "changing back to project "

cd ..

echo "running the server"

python manage.py runserver





