echo "Initializing database with Aerich"
aerich init -t app.database.TORTOISE_ORM
aerich init-db
echo "End of initialization"

## Remove database
# volumnes in Docker Desktop Windows --> look for volume carlemany-backend-data and delete
# Down code only for Linux
#  docker volume ls | grep carlemany-backend-data | awk '{ print $2 }' | xargs docker volume rm