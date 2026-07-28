from datetime import datetime, timezone
from io import BytesIO
from typing import IO, Any, Literal

import pydantic
from abc import ABC, abstractmethod


class InitOrDeleteBucketResponse(pydantic.BaseModel):
    status: Literal["success", "error"]
    bucket_name: str
    bucket_uri: str


class BucketInfo(pydantic.BaseModel):
    name: str
    uri: str
    created_at: pydantic.AwareDatetime
    region: str | None = None
    storage_class: str | None = None
    total_objects: int | None = None
    total_size: int | None = None
    public_metadata_readable: bool = False
    public_content_readable: bool = False


class InfoBucketResponse(pydantic.BaseModel):
    status: Literal["success", "error"]
    bucket_info: BucketInfo | None = None
    error_message: str | None = None


class ListBucketsResponse(pydantic.BaseModel):
    status: Literal["success", "error"]
    buckets: list[BucketInfo] | None = None
    error_message: str | None = None


class ObjectUploadRequest(pydantic.BaseModel):
    bucket_name: str
    object_name: str
    mime_type: str = "application/octet-stream"
    extra_metadata: dict[str, pydantic.JsonValue] | None = None


class ObjectUploadTaskResponse(pydantic.BaseModel):
    status: Literal["upload-success", "upload-error", "upload-in-progress"]
    total_bytes_uploaded: int | None = None
    total_bytes_known: int | None = None
    task_id: str
    error_message: str | None = None


class ObjectInfoResponse(pydantic.BaseModel):
    status: Literal["success", "error"]
    object_name: str | None = None
    bucket_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    created_at: pydantic.AwareDatetime | None = None
    last_modified_at: pydantic.AwareDatetime | None = None
    extra_metadata: dict[str, pydantic.JsonValue] | None = None
    error_message: str | None = None


class ObjectInfoUpdate(pydantic.BaseModel):
    mime_type: str | None = None
    # size_bytes: int | None = None
    last_modified_at: pydantic.AwareDatetime | None = None
    extra_metadata: dict[str, pydantic.JsonValue] | None = None


class ObjectInfoUpdateResponse(pydantic.BaseModel):
    status: Literal["success", "error"]
    object_info: ObjectInfoUpdate | None = None
    error_message: str | None = None


class DeleteObjectResponse(pydantic.BaseModel):
    status: Literal["success", "error"]
    object_name: str | None = None
    bucket_name: str | None = None
    error_message: str | None = None


class ObjectStorage(ABC):
    @abstractmethod
    def init_bucket(
        self, name: str, config: dict[str, Any]
    ) -> InitOrDeleteBucketResponse: ...
    @abstractmethod
    def bucket_info(self, name: str) -> InfoBucketResponse: ...
    @abstractmethod
    def list_buckets(self) -> ListBucketsResponse: ...
    @abstractmethod
    def delete_bucket(self, name: str) -> InitOrDeleteBucketResponse: ...

    # objects

    @abstractmethod
    def upload_object(
        self, request: ObjectUploadRequest, data: IO[bytes]
    ) -> ObjectUploadTaskResponse: ...

    @abstractmethod
    def get_upload_task(self, task_id: str) -> ObjectUploadTaskResponse: ...

    @abstractmethod
    def query_objects(
        self, bucket_name: str, prefix: str | None = None
    ) -> list[ObjectInfoResponse]: ...

    @abstractmethod
    def get_object(self, bucket_name: str, object_name: str) -> ObjectInfoResponse: ...

    @abstractmethod
    def open_object(self, bucket_name: str, object_name: str) -> IO[bytes]: ...

    @abstractmethod
    def update_object(
        self, bucket_name: str, object_name: str, update: ObjectInfoUpdate
    ) -> ObjectInfoUpdateResponse: ...

    @abstractmethod
    def delete_object(
        self, bucket_name: str, object_name: str
    ) -> DeleteObjectResponse: ...


class InMemoryObjectStorage(ObjectStorage):
    def __init__(self):
        self.buckets: dict[str, BucketInfo] = {}
        self.objects: dict[tuple[str, str], ObjectInfoResponse] = {}
        self.upload_tasks: dict[str, ObjectUploadTaskResponse] = {}
        self.objects_blob: dict[tuple[str, str], bytes] = {}

    def init_bucket(
        self, name: str, config: dict[str, Any]
    ) -> InitOrDeleteBucketResponse:
        if name in self.buckets:
            return InitOrDeleteBucketResponse(
                status="error",
                bucket_name=name,
                bucket_uri=f"memory://{name}",
            )
        bucket_info = BucketInfo(
            name=name,
            uri=f"memory://{name}",
            created_at=datetime.now(timezone.utc),
            region=config.get("region"),
            storage_class=config.get("storage_class"),
        )
        self.buckets[name] = bucket_info
        return InitOrDeleteBucketResponse(
            status="success",
            bucket_name=name,
            bucket_uri=bucket_info.uri,
        )

    def bucket_info(self, name: str) -> InfoBucketResponse:
        if name not in self.buckets:
            return InfoBucketResponse(
                status="error",
                error_message=f"Bucket '{name}' not found.",
            )
        return InfoBucketResponse(
            status="success",
            bucket_info=self.buckets[name],
        )

    def list_buckets(self) -> ListBucketsResponse:
        return ListBucketsResponse(
            status="success",
            buckets=list(self.buckets.values()),
        )

    def delete_bucket(self, name: str) -> InitOrDeleteBucketResponse:
        if name not in self.buckets:
            return InitOrDeleteBucketResponse(
                status="error",
                bucket_name=name,
                bucket_uri=f"memory://{name}",
            )
        del self.buckets[name]
        # Also delete all objects in the bucket
        self.objects = {
            (b_name, o_name): obj_info
            for (b_name, o_name), obj_info in self.objects.items()
            if b_name != name
        }
        self.objects_blob = {
            (b_name, o_name): blob
            for (b_name, o_name), blob in self.objects_blob.items()
            if b_name != name
        }
        return InitOrDeleteBucketResponse(
            status="success",
            bucket_name=name,
            bucket_uri=f"memory://{name}",
        )

    def upload_object(
        self, request: ObjectUploadRequest, data: IO[bytes]
    ) -> ObjectUploadTaskResponse:
        if request.bucket_name not in self.buckets:
            return ObjectUploadTaskResponse(
                status="upload-error",
                task_id="",
                error_message=f"Bucket '{request.bucket_name}' not found.",
            )

        # For simplicity, we will just read the data and store it in memory
        content = data.read()
        object_info = ObjectInfoResponse(
            status="success",
            object_name=request.object_name,
            bucket_name=request.bucket_name,
            mime_type=request.mime_type,
            size_bytes=len(content),
            created_at=datetime.now(timezone.utc),
            last_modified_at=datetime.now(timezone.utc),
        )
        self.objects[(request.bucket_name, request.object_name)] = object_info
        self.objects_blob[(request.bucket_name, request.object_name)] = content
        task_id = f"task-{len(self.upload_tasks) + 1}"
        upload_task_response = ObjectUploadTaskResponse(
            status="upload-success",
            total_bytes_uploaded=len(content),
            total_bytes_known=len(content),
            task_id=task_id,
        )
        self.upload_tasks[task_id] = upload_task_response
        return upload_task_response

    def get_upload_task(self, task_id: str) -> ObjectUploadTaskResponse:
        return self.upload_tasks.get(
            task_id,
            ObjectUploadTaskResponse(
                status="upload-error",
                task_id=task_id,
                error_message="Task not found.",
            ),
        )

    def get_object(self, bucket_name: str, object_name: str) -> ObjectInfoResponse:
        return self.objects.get(
            (bucket_name, object_name),
            ObjectInfoResponse(
                status="error",
                error_message=f"Object '{object_name}' in bucket '{bucket_name}' not found.",
            ),
        )

    def open_object(self, bucket_name: str, object_name: str) -> IO[bytes]:
        obj_info = self.get_object(bucket_name, object_name)
        if obj_info.status == "error":
            raise FileNotFoundError(obj_info.error_message)
        # For simplicity, we will return a BytesIO object with the actual content
        from io import BytesIO

        return BytesIO(self.objects_blob[(bucket_name, object_name)])

    def delete_object(self, bucket_name, object_name):
        if (bucket_name, object_name) not in self.objects:
            return DeleteObjectResponse(
                status="error",
                object_name=object_name,
                bucket_name=bucket_name,
                error_message=f"Object '{object_name}' in bucket '{bucket_name}' not found.",
            )
        del self.objects[(bucket_name, object_name)]
        del self.objects_blob[(bucket_name, object_name)]
        return DeleteObjectResponse(
            status="success",
            object_name=object_name,
            bucket_name=bucket_name,
        )

    def update_object(
        self, bucket_name: str, object_name: str, update: ObjectInfoUpdate
    ) -> ObjectInfoUpdateResponse:
        obj_info = self.get_object(bucket_name, object_name)
        if obj_info.status == "error":
            return ObjectInfoUpdateResponse(
                status="error",
                error_message=obj_info.error_message,
            )
        # Update the object info
        if update.mime_type is not None:
            obj_info.mime_type = update.mime_type
        # if update.size_bytes is not None:
        #     obj_info.size_bytes = update.size_bytes
        if update.last_modified_at is not None:
            obj_info.last_modified_at = update.last_modified_at
        self.objects[(bucket_name, object_name)] = obj_info
        return ObjectInfoUpdateResponse(
            status="success",
            object_info=update,
        )

    def query_objects(self, bucket_name, prefix=None):
        if bucket_name not in self.buckets:
            return []
        result = []
        for (b_name, o_name), obj_info in self.objects.items():
            if b_name == bucket_name and (prefix is None or o_name.startswith(prefix)):
                result.append(obj_info)
        return result


storage = InMemoryObjectStorage()
p = storage.init_bucket(
    "test-bucket", {"region": "us-east-1", "storage_class": "standard"}
)
p = storage.upload_object(
    ObjectUploadRequest(
        bucket_name="test-bucket",
        object_name="test-object.txt",
        mime_type="text/plain",
    ),
    data=BytesIO(b"Hello, World!"),
)
print(storage.query_objects("test-bucket"))
