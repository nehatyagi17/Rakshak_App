from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.db import contacts_col
from bson.objectid import ObjectId
from rest_framework.permissions import IsAuthenticated

class ContactListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        contacts = list(contacts_col.find({"user_id": {"$in": [user_id, ObjectId(user_id)]}}))
        for contact in contacts:
            contact["_id"] = str(contact["_id"])
        return Response(contacts, status=status.HTTP_200_OK)

class ContactAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.id
        data = request.data
        
        name = data.get('name')
        phone = data.get('phone')
        email = data.get('email')
        
        if not name or not phone:
            return Response({"error": "Name and phone are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        contact_doc = {
            "user_id": user_id,
            "name": name,
            "phone": phone,
            "email": email
        }
        
        result = contacts_col.insert_one(contact_doc)
        contact_doc["_id"] = str(result.inserted_id)
        
        return Response(contact_doc, status=status.HTTP_201_CREATED)

class ContactRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, contact_id):
        user_id = request.user.id
        
        try:
            result = contacts_col.delete_one({"_id": ObjectId(contact_id), "user_id": {"$in": [user_id, ObjectId(user_id)]}})
            if result.deleted_count == 0:
                return Response({"error": "Contact not found or not authorized"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Contact removed successfully"}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Invalid contact ID"}, status=status.HTTP_400_BAD_REQUEST)
