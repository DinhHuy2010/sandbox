"""
dataclass Person
    ->field[name, dataclass.types.core.UnvalidatedString]
    ->field[age,
        dataclass.types.core.ValidatedInt
            ->gt[0]
            ->lt[150]
        ]
    ->field[bio,
        dataclass.types.core.ValidatedString
            ->max_length[1024]
            ->min_length[0],
        required[bool:false]
        ]
dataclass.core.build_instance Person
    ->field[name, "John Doe"]
    ->field[age, 30]
    ->field[bio, "Software developer with 10 years of experience."]
>> export_as person
dataclass.core.print_instance
    ->instance[person]

cluster
    ->field[cpu,
        ->field[cores, 192]
        ->field[threads, $.cores * 4]
    ],
    ->field[memory,
        ->field[sticks, array[
            object->
                ->field[size, unit[GB, 512]]
                ->field[type, "DDR5"],
                ->field[ecc, bool:true]
            *($.sticks[-1] * 128)
        ]
    ]
    ->field[storage,
        ->field[disks, array[
            object->
                ->field[size, unit[TB, 4]]
                ->field[type, "SSD-NVMe"]
            *($.disks[-1] * 8)
            object->
                ->field[size, unit[TB, 8]]
                ->field[type, "HDD"]
                ->field[raid, bool:true],
            *($.disks[-1] * 64)
        ]
>> cluster
supercomputer = cluster*128
"""
