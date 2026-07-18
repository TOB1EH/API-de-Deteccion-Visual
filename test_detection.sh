curl -X POST http://localhost/api/detections \
       -H "Authorization: Bearer <token>" \
       -F "image=@tests/test_images/person.jpg" \
       -F "lat=-34.6037" \
       -F "lon=-58.3816"
