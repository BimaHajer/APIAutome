from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from user.serializers import UserSerializer


class UserAddView(APIView):
    def post(self,request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
class UserListView(APIView):
    def get(self,request):
        users = UserCustomer.objects.all()
        serializer = UserSerializer(users,many=True)
        return Response(serializer.data)
class UserDetailView(APIView):
    def get(self,request,pk):
        user = UserCustomer.objects.get(id=pk)
        serializer = UserSerializer(user)
        return Response(serializer.data)
class UserUpdateView(APIView):
    def put(self,request,pk):
        user = UserCustomer.objects.get(id=pk)
        serializer = UserSerializer(user,data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    def patch(self,request,pk):
        user = UserCustomer.objects.get(id=pk)
        serializer = UserSerializer(user,data=request.data,partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
class UserDeleteView(APIView):
    def delete(self,request,pk):
        user = UserCustomer.objects.get(id=pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)